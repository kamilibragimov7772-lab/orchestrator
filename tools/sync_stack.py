"""Opt-in bridge. Exact-file allowlist, exclusive lock and checked Git outcomes.

Diverged branches require manual reconciliation. No autostash, reset or force push.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from secret_scan import detect, private_path, scan_repo


class SyncError(Exception):
    pass


def git(root, *args, allowed=(0,)):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    env.setdefault('GIT_SSH_COMMAND', 'ssh -o BatchMode=yes -o ConnectTimeout=10')
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, env=env, timeout=45)
    if p.returncode not in allowed:
        raise SyncError(f'git {args[0]} failed (exit {p.returncode}); inspect locally')
    return p.returncode, p.stdout.decode('utf-8', errors='strict').strip()


def manifest(root):
    names = []
    for line in (root / 'sync-allowlist.txt').read_text(encoding='utf-8').splitlines():
        name = line.strip()
        if not name or name.startswith('#'): continue
        p = PurePosixPath(name)
        if (p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name
                or any(c in name for c in '*?[') or private_path(name)):
            raise SyncError('unsafe allowlist entry')
        target = root / name
        if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
            raise SyncError('allowlist escapes stack root')
        names.append(name)
    if not names: raise SyncError('empty allowlist')
    return sorted(set(names))


def sync(root, remote='origin', branch='main'):
    root = root.resolve()
    if git(root, 'rev-parse', '--show-toplevel')[1].replace('\\', '/') != root.as_posix():
        raise SyncError('stack root must be the repository root')
    gd = Path(git(root, 'rev-parse', '--absolute-git-dir')[1])
    lock = gd / 'orchestrator-sync.lock'
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SyncError('sync already running; inspect stale lock manually')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'pid': os.getpid(), 'started': datetime.now(timezone.utc).isoformat()}, stream)
        index_lock = Path(git(root, 'rev-parse', '--git-path', 'index.lock')[1])
        if not index_lock.is_absolute(): index_lock = root / index_lock
        if index_lock.exists(): raise SyncError('Git index is locked')
        if any((gd / x).exists() for x in ('rebase-merge', 'rebase-apply', 'MERGE_HEAD', 'CHERRY_PICK_HEAD')):
            raise SyncError('Git operation already in progress')
        if git(root, 'branch', '--show-current')[1] != branch:
            raise SyncError('unexpected branch')
        if git(root, 'diff', '--cached', '--quiet', allowed=(0, 1))[0]:
            raise SyncError('user has staged changes; index preserved')
        allowed = manifest(root)
        tracked = set(git(root, 'ls-files', '-z')[1].split('\0'))
        selected = [n for n in allowed if (root / n).is_file() or n in tracked]
        if not selected: raise SyncError('no permitted files')
        for name in selected:
            p = root / name
            if p.is_file() and detect(p.read_text(encoding='utf-8', errors='replace')):
                raise SyncError('credential pattern in allowlisted file; sync blocked')
        git(root, 'add', '-A', '--', *[':(literal)' + n for n in selected])
        staged = set(filter(None, git(root, 'diff', '--cached', '--name-only', '-z')[1].split('\0')))
        if staged - set(allowed): raise SyncError('index changed concurrently; sync blocked')
        if scan_repo(root, staged=True):
            raise SyncError('credential or private path in staged snapshot; sync blocked')
        committed = bool(staged)
        if committed: git(root, 'commit', '-m', 'Sync explicitly allowlisted stack files')
        if git(root, 'diff', '--quiet', allowed=(0, 1))[0]:
            raise SyncError('unmanaged tracked changes; local commit kept, remote untouched')
        git(root, 'fetch', '--no-tags', remote, branch)
        commits = git(root, 'rev-list', 'FETCH_HEAD..HEAD')[1].splitlines()
        if len(commits) > 50: raise SyncError('outgoing history exceeds 50-commit scan budget; inspect manually')
        for commit in commits:
            outgoing = set(filter(None, git(root, 'ls-tree', '-r', '--name-only', '-z', commit)[1].split('\0')))
            if outgoing - set(allowed): raise SyncError('outgoing history contains non-allowlisted paths')
            for name in outgoing:
                if detect(git(root, 'show', commit + ':' + name)[1]):
                    raise SyncError('credential pattern in outgoing history; sync blocked')
        git(root, 'merge', '--ff-only', 'FETCH_HEAD')
        git(root, 'push', remote, 'HEAD:refs/heads/' + branch)
        return {'status': 'success', 'committed': committed}
    finally:
        lock.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--remote', default='origin')
    p.add_argument('--branch', default='main')
    args = p.parse_args()
    try:
        result = sync(args.root, args.remote, args.branch)
    except (SyncError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        result = {'status': 'failed', 'reason': str(exc) if isinstance(exc, SyncError) else type(exc).__name__}
    print(json.dumps(result))
    return 0 if result['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())

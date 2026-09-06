# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""Plan or apply a collision-safe installation. Never overwrites unrelated files.

Use an explicit destination. No network, credential setup, export or remote sync.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE_AGENTS = {'brief-architect', 'strategy-researcher', 'decision-analyst', 'synthesizer',
               'task-author', 'knowledge-curator', 'acceptance-gate'}


def selected_files(mode):
    result = []
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if not p.is_file() or any(x in {'.git', '__pycache__', 'node_modules', 'audit_9_5'} for x in rel.parts): continue
        if rel.parts[0] not in {'agents', 'commands', 'skills', 'hooks', 'tools', 'tests', 'githooks'} and not (
                p.parent == ROOT and (p.name.startswith('_') or p.name in {'EVAL_PROMPT.md', 'sync-allowlist.txt'})):
            continue
        if mode == 'minimal':
            if rel.parts[0] == 'skills': continue
            if rel.parts[0] == 'agents' and rel.parts[1] != '_shared' and p.stem not in CORE_AGENTS: continue
            if rel.parts[0] == 'commands' and p.stem not in {'orchestr', 'priyomka', 'checkpoint'}: continue
            if rel.parts[:2] in {('tools', 'silero-tts'), ('tools', 'kinetic-promo')}: continue
        result.append(rel)
    return sorted(result)


def hooks(destination):
    tool = destination / 'tools/guard.py'
    return {'PreToolUse': [
        {'matcher': 'Write|Edit|Bash|PowerShell', 'hooks': [{'type': 'command', 'command': sys.executable,
          'args': [str(tool), 'secret'], 'timeout': 15}]},
        {'matcher': 'Bash|PowerShell', 'hooks': [{'type': 'command', 'command': sys.executable,
          'args': [str(tool), 'risk'], 'timeout': 15}]},
    ]}


def merge_settings(current, additions, env):
    # Round-trip makes a separate value. Never mutate caller data during preflight.
    cfg = json.loads(json.dumps(current))
    if not isinstance(cfg, dict): raise ValueError('settings must be a JSON object')
    groups = cfg.setdefault('hooks', {})
    if not isinstance(groups, dict): raise ValueError('hooks must be an object')
    for event, items in additions.items():
        target = groups.setdefault(event, [])
        if not isinstance(target, list): raise ValueError('event hooks must be a list')
        for item in items:
            if item not in target: target.append(item)
    target_env = cfg.setdefault('env', {})
    if not isinstance(target_env, dict): raise ValueError('env must be an object')
    for key, value in env.items():
        if key in target_env and target_env[key] != value:
            raise ValueError('existing environment setting conflicts: ' + key)
        target_env[key] = value
    return cfg


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.orchestrator-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)

def validate_parent_chain(path, root):
    """Reject file or symlink parents before any installation write."""
    current = path.parent
    root = root.resolve()
    while current != root:
        if not current.resolve().is_relative_to(root):
            raise ValueError('unsafe destination parent')
        if current.exists() and (current.is_symlink() or not current.is_dir()):
            raise ValueError('destination parent is not a directory: ' + str(current.relative_to(root)))
        current = current.parent


def install(destination, vault, mode='full', apply=False):
    destination, vault = Path(destination).resolve(), Path(vault).resolve()
    if destination == ROOT or ROOT.is_relative_to(destination) or destination.is_relative_to(ROOT):
        raise ValueError('installation destination must be separate from source checkout')
    files = selected_files(mode)
    writes, conflicts = [], []
    for rel in files:
        source, target = ROOT / rel, destination / rel
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT): raise ValueError('unsafe source')
        if not target.resolve().is_relative_to(destination) or target.is_symlink(): raise ValueError('unsafe destination')
        data = source.read_bytes()
        if rel.suffix == '.md':
            content = data.decode('utf-8-sig')
            content = content.replace('~/.claude', destination.as_posix()).replace('~/vault', vault.as_posix())
            content = content.replace('<VAULT_ROOT>', vault.as_posix())
            data = content.encode('utf-8')
        if target.exists() and (not target.is_file() or target.read_bytes() != data): conflicts.append(str(rel))
        elif not target.exists(): writes.append((target, data))
    if conflicts: raise ValueError('existing files differ; preserve them and choose a fresh destination: ' + ', '.join(conflicts[:8]))
    settings = destination / 'settings.json'
    if settings.is_symlink() or not settings.resolve().is_relative_to(destination): raise ValueError('unsafe settings path')
    cfg = json.loads(settings.read_text(encoding='utf-8-sig')) if settings.exists() else {}
    cfg = merge_settings(cfg, hooks(destination), {'CLAUDE_HOME': str(destination), 'VAULT_ROOT': str(vault)})
    # No transcript export, remote sync or model process is installed as an automatic hook.
    entry = destination / 'CLAUDE.md'
    if entry.is_symlink() or not entry.resolve().is_relative_to(destination): raise ValueError('unsafe entry file')
    entry_text = entry.read_text(encoding='utf-8-sig') if entry.exists() else ''
    marker = '<!-- orchestrator-managed-entry -->'
    if marker not in entry_text:
        entry_text += ('\n' + marker + '\n## Orchestrator\n'
                       'When the user invokes /orchestr, read `' + destination.as_posix() + '/_orchestr_protocol.md`.\n'
                       'Resolve all stack paths under `' + destination.as_posix() + '` and knowledge-base paths under `' + vault.as_posix() + '`.\n'
                       'Only the orchestrator or an explicit command wrapper delegates these agents.\n'
                       'Optional integrations may be unavailable; report missing inputs instead of inventing results.\n')
    result = {'status': 'planned', 'mode': mode, 'new_files': len(writes), 'destination': str(destination),
              'next': 'Run doctor.py --installed before using agents. Optional plugins and models require separate setup.'}
    seeds = {'README.md': '# Knowledge base\nProject source material belongs here.\n',
             'CLAUDE.md': '# Knowledge base entry\nRead project sources before using them.\n',
             '_orchestr/00_runs_index.md': '# Run index\n', '_orchestr/_AGENT_USAGE.md': '# Agent usage\n',
             '_orchestr/_CONFIDENTIAL_TOPICS.md': '# Confidential topics\nNo topics configured.\n'}
    directories = ('_orchestr/_ACTIVE', '_orchestr/_ARCHIVE', '08-Работа-Claude', '11-Decisions-Log')
    for name in (*directories, *seeds):
        target = vault / name
        if not target.resolve().is_relative_to(vault) or target.is_symlink():
            raise ValueError('unsafe vault path')
        for parent in target.parents:
            if parent == vault.parent: break
            if parent.exists() and not parent.is_dir(): raise ValueError('vault parent is not a directory')
        if target.exists() and (target.is_dir() != (name in directories)):
            raise ValueError('vault file/directory collision')
    # Complete preflight before the first write, including every target parent.
    for path, _ in writes:
        validate_parent_chain(path, destination)
    for path in (settings, entry):
        validate_parent_chain(path, destination)
    for name in (*directories, *seeds):
        validate_parent_chain(vault / name, vault)
    if apply:
        for path, data in writes: atomic_write(path, data)
        atomic_write(settings, (json.dumps(cfg, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        atomic_write(entry, entry_text.encode('utf-8'))
        for name in directories:
            target = vault / name
            if not target.resolve().is_relative_to(vault): raise ValueError('vault path escapes root')
            target.mkdir(parents=True, exist_ok=True)
        for name, value in seeds.items():
            target = vault / name
            if not target.resolve().is_relative_to(vault) or target.is_symlink(): raise ValueError('unsafe vault seed')
            if not target.exists(): atomic_write(target, value.encode('utf-8'))
        result['status'] = 'installed'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', required=True, type=Path)
    p.add_argument('--vault', required=True, type=Path)
    p.add_argument('--mode', choices=['minimal', 'full'], default='full')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    try:
        print(json.dumps(install(args.destination, args.vault, args.mode, args.apply), ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print('Installation failed: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

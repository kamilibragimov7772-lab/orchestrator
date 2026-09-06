"""Heuristic credential scanner. Independent Gitleaks history scan runs in CI.

Only pattern types and paths are reported; matching values never leave this module.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = {
    'anthropic': r'sk-ant-[A-Za-z0-9_-]{20,}',
    'openai': r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',
    'openrouter': r'sk-or-v1-[A-Za-z0-9_-]{20,}',
    'github': r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'gitlab': r'glpat-[A-Za-z0-9_-]{20,}',
    'aws': r'(?:AKIA|ASIA)[0-9A-Z]{16}',
    'slack': r'xox[baprs]-[A-Za-z0-9-]{10,}',
    'telegram': r'\b[0-9]{8,12}:[A-Za-z0-9_-]{35}\b',
    'private-key': r'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----',
    'google': r'AIza[0-9A-Za-z_-]{35}',
    'stripe': r'(?:sk|rk)_live_[A-Za-z0-9]{20,}',
    'huggingface': r'hf_[A-Za-z0-9]{30,}',
    'connection-string': r'(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/]+:[^\s@]{5,}@',
    'azure-account-key': r'(?i)AccountKey=[A-Za-z0-9+/]{40,}={0,2}',
    'jwt': r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
}
COMPILED = {name: re.compile(pattern) for name, pattern in PATTERNS.items()}
PRIVATE_NAMES = {'.env', '.claude.json', '.credentials.json', 'settings.json', 'settings.local.json'}


def detect(text):
    return sorted(name for name, pattern in COMPILED.items() if pattern.search(text))


def private_path(path):
    p = Path(path)
    return (p.name in PRIVATE_NAMES or p.name.endswith(('.env', '.jsonl', '.log', '.bak'))
            or '.bak-' in p.name or any(x in {'sessions', 'backups', 'vault', '.obsidian'} for x in p.parts))


def scan_repo(root, staged=False):
    args = ['git', '-C', str(root), 'diff', '--cached', '--name-only', '--diff-filter=ACM', '-z'] if staged else [
        'git', '-C', str(root), 'ls-files', '-z']
    names = subprocess.check_output(args).decode('utf-8').split('\0')
    findings = []
    for name in filter(None, names):
        reasons = ['private-path'] if private_path(name) else []
        if staged:
            data = subprocess.check_output(['git', '-C', str(root), 'show', ':' + name])
        else:
            path = root / name
            if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
                findings.append({'file': name, 'types': ['symlink-or-external-path']}); continue
            data = path.read_bytes()
        reasons += detect(data.decode('utf-8', errors='replace'))
        if reasons: findings.append({'file': name, 'types': reasons})
    return findings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--staged', action='store_true')
    args = p.parse_args()
    try:
        findings = scan_repo(args.root, args.staged)
        print(json.dumps({'layer': 'heuristic', 'findings': findings}, ensure_ascii=True, indent=2))
        return 1 if findings else 0
    except (OSError, subprocess.SubprocessError):
        print('Secret scan NOT CHECKED: input or Git failure', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

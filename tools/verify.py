"""One reproducible core check command for a checkout or installed distribution."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys


def verify(root, security=True):
    for path in root.rglob('*.py'):
        if any(x in {'.git', 'node_modules', '__pycache__'} for x in path.parts): continue
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for path in [root / 'settings.example.json']:
        if path.exists(): json.loads(path.read_text(encoding='utf-8-sig'))
    env = dict(os.environ, CLAUDE_HOME=str(root), PYTHONIOENCODING='utf-8')
    cmds = [
        [sys.executable, 'tools/agent-lint.py', '--quiet'],
        [sys.executable, 'tools/gotovo-counter.py', '--selftest'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
    ]
    if security: cmds.append([sys.executable, 'tools/secret_scan.py', '--root', str(root)])
    failed = False
    for cmd in cmds:
        print('CHECK ' + ' '.join(cmd), flush=True)
        p = subprocess.run(cmd, cwd=root, env=env, timeout=240)
        print('EXIT ' + str(p.returncode), flush=True)
        failed = failed or p.returncode != 0
    return 1 if failed else 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--without-git-scan', action='store_true', help='For installed distribution without Git; scan source release separately.')
    args = p.parse_args()
    try: sys.exit(verify(args.root.resolve(), not args.without_git_scan))
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as exc:
        print('Verification failed: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(2)

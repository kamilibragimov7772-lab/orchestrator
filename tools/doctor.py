"""Report local runtime readiness, keeping required and optional checks distinct."""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def inspect(root, installed=False):
    root = Path(root).resolve()
    result = []
    def add(name, required, status, detail):
        result.append({'check': name, 'required': required, 'status': status, 'detail': detail})
    add('python', True, 'pass' if sys.version_info >= (3, 10) else 'fail', sys.version.split()[0])
    add('git', True, 'pass' if shutil.which('git') else 'fail', 'PATH executable')
    for name in ('claude', 'node', 'npm', 'ffmpeg', 'gitleaks', 'pwsh'):
        add(name, installed and name == 'claude', 'available' if shutil.which(name) else 'not-installed',
            'availability only; authentication and integration NOT TESTED')
    for path in root.rglob('*.py'):
        if any(x in {'.git', 'node_modules', '__pycache__'} for x in path.parts): continue
        try: ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except (SyntaxError, UnicodeError, OSError): add(str(path.relative_to(root)), True, 'fail', 'Python parse error')
    cmd = [sys.executable, str(root / 'tools/agent-lint.py'), '--quiet']
    p = subprocess.run(cmd, capture_output=True, encoding='utf-8', env=dict(os.environ, CLAUDE_HOME=str(root)), timeout=30)
    add('agent-contract-lint', True, 'pass' if p.returncode == 0 else 'fail', p.stdout.strip() or p.stderr.strip())
    if installed:
        settings = root / 'settings.json'
        try:
            cfg = json.loads(settings.read_text(encoding='utf-8-sig'))
            handlers = [(item.get('matcher', ''), h) for item in cfg.get('hooks', {}).get('PreToolUse', []) for h in item.get('hooks', [])]
            expected = root / 'tools/guard.py'
            guard_ok = expected.is_file() and not expected.is_symlink()
            interpreter_ok = bool(shutil.which(sys.executable))
            for kind in ('secret', 'risk'):
                wanted = 'Write|Edit|Bash|PowerShell' if kind == 'secret' else 'Bash|PowerShell'
                wired = any(matcher == wanted and h.get('type') == 'command' and h.get('args') == [str(expected), kind]
                            and h.get('command') == sys.executable for matcher, h in handlers)
                add(kind + '-guard-wiring', True, 'pass' if (guard_ok and interpreter_ok and wired) else 'fail', 'guard file, interpreter and exact matcher')
            smoke_ok = False; smoke_detail = 'portable hook execution'
            if guard_ok:
                benign = json.dumps({'tool_name': 'Write', 'tool_input': {'content': 'syntheticpayload'}}).encode()
                secret = json.dumps({'tool_name': 'Write', 'tool_input': {'content': 'sk-' + 'proj-' + 'A' * 44}}).encode()
                risky = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'git push --force origin main'}}).encode()
                try:
                    p1 = subprocess.run([sys.executable, str(expected), 'secret'], input=benign, capture_output=True, timeout=10)
                    p2 = subprocess.run([sys.executable, str(expected), 'secret'], input=secret, capture_output=True, timeout=10)
                    p3 = subprocess.run([sys.executable, str(expected), 'risk'], input=risky, capture_output=True, timeout=10)
                except subprocess.TimeoutExpired:
                    smoke_detail = 'guard smoke timed out'
                    p1 = p2 = p3 = None
                smoke_ok = bool(p1 and p2 and p3 and p1.returncode == 0 and p2.returncode == 2 and p3.returncode == 2)
                if not smoke_ok and p1 is not None: smoke_detail = 'unexpected guard exit code'
            add('guard-smoke', True, 'pass' if smoke_ok else 'fail', smoke_detail)
            vault = Path(cfg.get('env', {}).get('VAULT_ROOT', ''))
            add('vault', True, 'pass' if (vault / '_orchestr/_ACTIVE').is_dir() else 'fail', 'run directory exists')
        except (OSError, ValueError, TypeError): add('settings', True, 'fail', 'settings absent or invalid')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--installed', action='store_true')
    args = p.parse_args()
    try:
        checks = inspect(args.root, args.installed)
        failed = any(c['required'] and c['status'] not in {'pass', 'available'} for c in checks)
        print(json.dumps({'scope': 'static and local readiness only', 'status': 'fail' if failed else 'pass', 'checks': checks}, ensure_ascii=True, indent=2))
        sys.exit(1 if failed else 0)
    except (OSError, subprocess.SubprocessError):
        print('doctor: runtime error; NOT CHECKED', file=sys.stderr)
        sys.exit(2)

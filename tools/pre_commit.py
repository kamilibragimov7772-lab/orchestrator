# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""Validate the staged snapshot, never an unrelated home or unstaged fix."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from secret_scan import scan_repo


def check(root):
    findings = scan_repo(root, staged=True)
    if findings:
        print('pre-commit: credential/private-path finding; run tools/secret_scan.py --staged')
        return 1
    entries = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z']).decode().split('\0')
    for entry in filter(None, entries):
        meta, name = entry.split('\t', 1)
        if meta.split()[0] in {'120000', '160000'}:
            print('pre-commit: symlink/submodule requires a separately reviewed policy')
            return 1
    with tempfile.TemporaryDirectory(prefix='orchestrator-staged-test-') as tmp:
        snapshot = Path(tmp)
        subprocess.run(['git', '-C', str(root), 'checkout-index', '--all', '--prefix=' + snapshot.as_posix() + '/'],
                       check=True, capture_output=True)
        linter = snapshot / 'tools/agent-lint.py'
        if not linter.is_file():
            print('pre-commit: linter absent from staged snapshot; NOT CHECKED')
            return 1
        return subprocess.run([sys.executable, str(linter), '--quiet'],
                              env=dict(os.environ, CLAUDE_HOME=str(snapshot)), cwd=snapshot).returncode


if __name__ == '__main__':
    try:
        root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip())
        sys.exit(check(root))
    except (OSError, subprocess.SubprocessError):
        print('pre-commit: runtime error; validation NOT CHECKED', file=sys.stderr)
        sys.exit(1)

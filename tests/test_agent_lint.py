"""Synthetic clean-clone regression suite; no private backups or home directory."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CARD = """---
name: sample
description: A synthetic agent used to verify enforceable input and output contracts.
tools: Read, Write, Bash
---
## Work
Сохрани отчёт и посчитай результат.
## Input
`~/.claude/agents/_shared/input_gate.md`
## Output
`~/.claude/agents/_shared/definition_of_done.md`
"""


class AgentLintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stack = Path(self.tmp.name)
        shared = self.stack / 'agents' / '_shared'
        shared.mkdir(parents=True)
        for name in ('input_gate.md', 'definition_of_done.md'):
            (shared / name).write_text('Canonical test contract', encoding='utf-8')
        (shared / 'communication_contract.md').write_text('type: <brief|research>\n', encoding='utf-8')
        self.card = self.stack / 'agents' / 'sample.md'

    def lint(self, content=CARD, target=False):
        self.card.write_text(content, encoding='utf-8')
        env = dict(os.environ, CLAUDE_HOME=str(self.stack))
        args = [sys.executable, str(ROOT / 'tools' / 'agent-lint.py'), '--quiet']
        if target:
            args.append(str(self.card))
        return subprocess.run(args, env=env, capture_output=True, text=True, encoding='utf-8', timeout=20)

    def test_valid_card(self):
        p = self.lint()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_missing_bash_mutation(self):
        self.assertEqual(self.lint(CARD.replace(', Bash', '')).returncode, 1)

    def test_missing_dod_mutation(self):
        self.assertEqual(self.lint(CARD.replace('definition_of_done.md', 'missing.md')).returncode, 1)

    def test_missing_frontmatter_mutation(self):
        self.assertEqual(self.lint(CARD.split('---', 2)[2]).returncode, 1)

    def test_missing_name_mutation(self):
        self.assertEqual(self.lint(CARD.replace('name: sample\n', '')).returncode, 1)

    def test_local_path_resolves_in_selected_stack(self):
        self.assertEqual(self.lint(CARD + '\n`~/.claude/agents/absent.md`\n').returncode, 1)

    def test_unknown_metadata_mutation(self):
        self.assertEqual(self.lint(CARD + '\nmetadata:\n  type: invented\n').returncode, 1)

    def test_missing_contract_is_error(self):
        (self.stack / 'agents/_shared/communication_contract.md').unlink()
        self.assertEqual(self.lint().returncode, 2)

    def test_explicit_card_target(self):
        self.assertEqual(self.lint(CARD.replace(', Bash', ''), target=True).returncode, 1)

    def test_empty_stack_is_not_success(self):
        self.assertEqual(subprocess.run(
            [sys.executable, str(ROOT / 'tools/agent-lint.py')],
            env=dict(os.environ, CLAUDE_HOME=str(self.stack / 'empty')),
            capture_output=True, timeout=20).returncode, 2)


if __name__ == '__main__':
    unittest.main()

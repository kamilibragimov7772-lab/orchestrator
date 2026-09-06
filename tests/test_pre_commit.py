import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pre_commit
from test_agent_lint import CARD


class PreCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-index-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', str(self.root)], check=True, capture_output=True)
        (self.root / 'tools').mkdir()
        shutil.copyfile(ROOT / 'tools/agent-lint.py', self.root / 'tools/agent-lint.py')
        shared = self.root / 'agents/_shared'; shared.mkdir(parents=True)
        for name in ('input_gate.md', 'definition_of_done.md'):
            (shared / name).write_text('test contract')
        (shared / 'communication_contract.md').write_text('type: <brief|research>')
        self.card = self.root / 'agents/sample.md'
        self.card.write_text(CARD, encoding='utf-8')

    def stage(self):
        subprocess.run(['git', '-C', str(self.root), 'add', 'tools', 'agents'], check=True, capture_output=True)

    def test_good_index_passes(self):
        self.stage()
        self.assertEqual(pre_commit.check(self.root), 0)

    def test_unstaged_fix_cannot_hide_broken_index(self):
        self.card.write_text(CARD.replace(', Bash', ''), encoding='utf-8'); self.stage()
        self.card.write_text(CARD, encoding='utf-8')
        self.assertEqual(pre_commit.check(self.root), 1)

    def test_staged_secret_is_rejected(self):
        self.card.write_text(CARD + '\nsk-' + 'proj-' + 'A' * 44, encoding='utf-8'); self.stage()
        self.assertEqual(pre_commit.check(self.root), 1)


if __name__ == '__main__':
    unittest.main()

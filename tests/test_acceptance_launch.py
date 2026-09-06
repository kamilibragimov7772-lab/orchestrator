import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/acceptance-gate'))
import launch


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-review-test-')
        self.addCleanup(self.tmp.cleanup)
        self.vault = Path(self.tmp.name)
        self.archive = self.vault / '_orchestr/_ARCHIVE'; self.archive.mkdir(parents=True)
        self.run = self.archive / 'run-fixture.md'
        self.run.write_text('---\nstatus: "done" # completed\n---\n', encoding='utf-8')

    def test_archived_run_with_comment_is_found(self):
        self.assertEqual(launch.candidates(self.vault), [self.run])

    def test_reviewed_run_is_not_repeated(self):
        self.run.write_text(self.run.read_text() + '\n## Приёмка\n', encoding='utf-8')
        self.assertEqual(launch.candidates(self.vault), [])

    def test_existing_lock_is_preserved(self):
        lock = self.run.with_suffix('.md.acceptance.lock'); lock.write_text('another worker')
        self.assertEqual(launch.process_run(self.run, ROOT, 'unused')['status'], 'skipped')
        self.assertEqual(lock.read_text(), 'another worker')

    def test_success_exit_without_report_is_failure(self):
        with patch.object(launch.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{}', '')):
            self.assertEqual(launch.process_run(self.run, ROOT, 'fake')['status'], 'failed')
        self.assertFalse(self.run.with_suffix('.md.acceptance.lock').exists())

    def test_timeout_releases_lock(self):
        with patch.object(launch.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 1)):
            with self.assertRaises(subprocess.TimeoutExpired): launch.process_run(self.run, ROOT, 'fake')
        self.assertFalse(self.run.with_suffix('.md.acceptance.lock').exists())


if __name__ == '__main__':
    unittest.main()

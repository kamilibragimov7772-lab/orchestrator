import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sync_stack


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-sync-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'local'
        self.remote = self.base / 'remote.git'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Synthetic test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'core.hooksPath', str(self.repo / '.git/hooks'))
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.autocrlf', 'false')
        self.git('config', 'protocol.file.allow', 'always')
        (self.repo / 'README.md').write_text('initial\n')
        (self.repo / 'sync-allowlist.txt').write_text('README.md\nsync-allowlist.txt\n')
        self.git('add', 'README.md', 'sync-allowlist.txt')
        self.git('commit', '-m', 'baseline')
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.STDOUT).decode().strip()

    def test_unknown_secret_file_remains_untracked(self):
        (self.repo / 'secret.txt').write_text('private test content')
        (self.repo / 'README.md').write_text('changed\n')
        result = sync_stack.sync(self.repo)
        self.assertEqual(result['status'], 'success')
        self.assertIn('?? secret.txt', self.git('status', '--short'))
        self.assertNotIn('secret.txt', self.git('ls-tree', '-r', '--name-only', 'origin/main'))

    def test_existing_index_is_preserved(self):
        (self.repo / 'README.md').write_text('staged by user')
        self.git('add', 'README.md')
        before = self.git('diff', '--cached')
        with self.assertRaisesRegex(sync_stack.SyncError, 'staged changes'):
            sync_stack.sync(self.repo)
        self.assertEqual(before, self.git('diff', '--cached'))

    def test_index_lock_blocks_without_removing_it(self):
        lock = self.repo / '.git/index.lock'; lock.write_text('synthetic lock')
        with self.assertRaisesRegex(sync_stack.SyncError, 'index is locked'):
            sync_stack.sync(self.repo)
        self.assertTrue(lock.exists())

    def test_concurrent_git_client_cannot_stage_while_sync_owns_index_lock(self):
        (self.repo / 'README.md').write_text('concurrent\n')
        lock = self.repo / '.git/index.lock'
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            client = subprocess.run(['git', '-C', str(self.repo), 'add', 'README.md'], capture_output=True)
            self.assertNotEqual(client.returncode, 0)
            with self.assertRaises(sync_stack.SyncError): sync_stack.sync(self.repo)
            self.assertTrue(lock.exists())
        finally:
            lock.unlink()

    def test_git_add_interleaving_is_rejected(self):
        (self.repo / 'README.md').write_text('interleaved\n')
        original = sync_stack.git
        attempted = []
        def wrapped(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if args[:3] == ('diff', '--cached', '--quiet') and not attempted:
                attempted.append(True)
                client = subprocess.run(['git', '-C', str(self.repo), 'add', 'README.md'], capture_output=True)
                self.assertNotEqual(client.returncode, 0)
            return result
        with mock.patch.object(sync_stack, 'git', side_effect=wrapped):
            sync_stack.sync(self.repo)
        self.assertEqual(self.git('show', 'HEAD:README.md'), 'interleaved')

    def test_sync_lock_blocks_second_caller(self):
        lock = self.repo / '.git/orchestrator-sync.lock'; lock.write_text('first process')
        with self.assertRaisesRegex(sync_stack.SyncError, 'already running'):
            sync_stack.sync(self.repo)
        self.assertEqual(lock.read_text(), 'first process')

    def test_network_failure_is_not_success(self):
        self.git('remote', 'set-url', 'origin', str(self.base / 'missing.git'))
        (self.repo / 'README.md').write_text('retain local change')
        with self.assertRaises(sync_stack.SyncError):
            sync_stack.sync(self.repo)
        self.assertIn('retain local change', self.git('show', 'HEAD:README.md'))
        self.assertFalse((self.repo / '.git/orchestrator-sync.lock').exists())

    def test_credential_blocks_before_staging(self):
        (self.repo / 'README.md').write_text('sk-' + 'proj-' + 'A' * 45)
        with self.assertRaisesRegex(sync_stack.SyncError, 'credential'):
            sync_stack.sync(self.repo)
        self.assertEqual(self.git('diff', '--cached'), '')

    def test_allowlist_cannot_escape_root(self):
        (self.repo / 'sync-allowlist.txt').write_text('../outside.md\n')
        with self.assertRaises(sync_stack.SyncError):
            sync_stack.sync(self.repo)

    def test_wrong_branch_is_rejected(self):
        self.git('switch', '-c', 'feature')
        with self.assertRaisesRegex(sync_stack.SyncError, 'unexpected branch'):
            sync_stack.sync(self.repo)

    def test_commit_failure_is_observable(self):
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o755)
        before = self.git('rev-parse', 'HEAD')
        (self.repo / 'README.md').write_text('change rejected by hook')
        with self.assertRaisesRegex(sync_stack.SyncError, 'commit failed'):
            sync_stack.sync(self.repo)
        self.assertEqual(before, self.git('rev-parse', 'HEAD'))

    def test_failed_push_is_observable(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o755)
        (self.repo / 'README.md').write_text('change rejected by remote')
        with self.assertRaisesRegex(sync_stack.SyncError, 'push failed'):
            sync_stack.sync(self.repo)

    def test_idempotent_clean_sync(self):
        before = self.git('rev-parse', 'HEAD')
        self.assertFalse(sync_stack.sync(self.repo)['committed'])
        self.assertEqual(before, self.git('rev-parse', 'HEAD'))

    def test_added_then_removed_private_file_cannot_leave_in_history(self):
        private = self.repo / 'secret.txt'; private.write_text('private history')
        self.git('add', 'secret.txt'); self.git('commit', '-m', 'synthetic private commit')
        self.git('rm', 'secret.txt'); self.git('commit', '-m', 'remove private file')
        with self.assertRaisesRegex(sync_stack.SyncError, 'history contains non-allowlisted'):
            sync_stack.sync(self.repo)

    def test_removed_credential_in_allowed_file_still_blocks_history(self):
        readme = self.repo / 'README.md'
        readme.write_text('sk-' + 'proj-' + 'B' * 44)
        self.git('add', 'README.md'); self.git('commit', '-m', 'synthetic credential')
        readme.write_text('initial\n')
        self.git('add', 'README.md'); self.git('commit', '-m', 'remove credential')
        with self.assertRaisesRegex(sync_stack.SyncError, 'credential pattern in outgoing history'):
            sync_stack.sync(self.repo)


if __name__ == '__main__':
    unittest.main()

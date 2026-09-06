from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import install


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-install-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.dest = self.base / 'stack with spaces'
        self.vault = self.base / 'vault'

    def test_dry_run_writes_nothing(self):
        self.assertEqual(install.install(self.dest, self.vault)['status'], 'planned')
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.vault.exists())

    def test_clean_minimal_install_and_repeat(self):
        result = install.install(self.dest, self.vault, 'minimal', True)
        self.assertEqual(result['status'], 'installed')
        self.assertEqual(len(list((self.dest / 'agents').glob('*.md'))), 7)
        self.assertIn(self.vault.resolve().as_posix(), (self.dest / 'CLAUDE.md').read_text(encoding='utf-8'))
        self.assertEqual(install.install(self.dest, self.vault, 'minimal', True)['new_files'], 0)

    def test_existing_card_collision_leaves_target_unchanged(self):
        card = self.dest / 'agents/brief-architect.md'; card.parent.mkdir(parents=True)
        card.write_text('user custom agent')
        with self.assertRaises(ValueError): install.install(self.dest, self.vault, 'full', True)
        self.assertEqual(card.read_text(), 'user custom agent')
        self.assertFalse((self.dest / 'settings.json').exists())

    def test_settings_merge_preserves_permissions_and_hooks(self):
        original = {'permissions': {'defaultMode': 'default'}, 'hooks': {'Stop': [{'hooks': [{'command': 'custom'}]}]}}
        merged = install.merge_settings(original, install.hooks(self.dest), {})
        self.assertEqual(merged['permissions'], original['permissions'])
        self.assertEqual(merged['hooks']['Stop'], original['hooks']['Stop'])
        self.assertNotIn('PreToolUse', original['hooks'])

    def test_malformed_settings_fail_preflight(self):
        self.dest.mkdir()
        (self.dest / 'settings.json').write_text('broken')
        with self.assertRaises(ValueError): install.install(self.dest, self.vault, apply=True)
        self.assertFalse((self.dest / 'agents').exists())

    def test_paths_are_exec_arguments_without_shell(self):
        item = install.hooks(self.dest)['PreToolUse'][0]['hooks'][0]
        self.assertEqual(item['command'], sys.executable)
        self.assertEqual(item['args'], [str(self.dest / 'tools/guard.py'), 'secret'])
        self.assertNotIn('shell', item)

    def test_vault_collision_is_found_before_stack_writes(self):
        self.vault.mkdir()
        (self.vault / '_orchestr').write_text('user content')
        with self.assertRaises((ValueError, OSError)):
            install.install(self.dest, self.vault, apply=True)
        self.assertFalse(self.dest.exists())

    def test_file_parent_is_rejected_before_any_stack_write(self):
        self.dest.mkdir()
        (self.dest / 'tools').write_text('user file')
        with self.assertRaises(ValueError):
            install.install(self.dest, self.vault, apply=True)
        self.assertFalse((self.dest / 'agents').exists())


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import export_session


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-export-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'sources'; self.source.mkdir()
        self.vault = self.root / 'vault'
        self.transcript = self.source / 'session.jsonl'
        self.token = 'sk-' + 'proj-' + 'x' * 44
        self.transcript.write_text(json.dumps({'text': self.token}), encoding='utf-8')
        self.event = {'transcript_path': str(self.transcript), 'session_id': '../../unsafe'}

    def test_disabled_is_side_effect_free(self):
        self.assertEqual(export_session.export({}, 'off', None, None)['status'], 'skipped')
        self.assertFalse(self.vault.exists())

    def test_redacts_without_mutating_source(self):
        result = export_session.export(self.event, 'redacted', self.vault, self.source)
        self.assertNotIn(self.token, Path(result['destination']).read_text())
        self.assertIn(self.token, self.transcript.read_text())

    def test_full_requires_explicit_mode(self):
        result = export_session.export(self.event, 'full', self.vault, self.source)
        self.assertIn(self.token, Path(result['destination']).read_text())

    def test_outside_transcript_root_is_rejected(self):
        with self.assertRaises(ValueError):
            export_session.export(self.event, 'redacted', self.vault, self.root / 'unrelated')

    def test_invalid_json_does_not_produce_export(self):
        self.transcript.write_text('broken')
        with self.assertRaises(ValueError):
            export_session.export(self.event, 'redacted', self.vault, self.source)
        self.assertFalse(self.vault.exists())

    def test_repeat_export_is_idempotent(self):
        first = export_session.export(self.event, 'redacted', self.vault, self.source)
        second = export_session.export(self.event, 'redacted', self.vault, self.source)
        self.assertEqual(first['destination'], second['destination'])
        self.assertEqual(len(list((self.vault / '_session_exports').iterdir())), 1)

    def test_empty_transcript_preserves_previous_export(self):
        first = export_session.export(self.event, 'redacted', self.vault, self.source)
        previous = Path(first['destination']).read_text()
        self.transcript.write_text('\n\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            export_session.export(self.event, 'redacted', self.vault, self.source)
        self.assertEqual(Path(first['destination']).read_text(), previous)


if __name__ == '__main__':
    unittest.main()

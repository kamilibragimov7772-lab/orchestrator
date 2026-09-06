import csv
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
inventory = module('inventory', 'tools/repo-inventory/inventory.py')
video = module('video_config', 'skills/video-montage/scripts/video_config.py')

class HelpersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='orchestrator-helpers-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'raw').mkdir()

    def test_inventory_failed_tools_never_report_zero_findings(self):
        with patch.object(inventory, 'have', return_value=True), patch.object(inventory, 'run', return_value=(2, '', 'synthetic failure')):
            for call in (lambda: inventory.tool_ruff(str(self.root), str(self.root)),
                         lambda: inventory.tool_vulture(str(self.root), str(self.root)),
                         lambda: inventory.tool_radon(str(self.root), str(self.root), {'py'})):
                self.assertIn('error', call())

    def test_inventory_does_not_accept_stale_duplicate_report(self):
        stale = self.root / 'raw/jscpd'; stale.mkdir()
        (stale / 'jscpd-report.json').write_text('{"statistics":{"total":{}}}')
        with patch.object(inventory, 'run', return_value=(1, '', 'failed')):
            self.assertIn('error', inventory.tool_jscpd(str(self.root), str(self.root), {'py'}))

    def test_vulture_findings_exit_is_valid(self):
        with patch.object(inventory, 'have', return_value=True), patch.object(inventory, 'run', return_value=(3, 'x.py:1 unused', '')):
            self.assertEqual(inventory.tool_vulture(str(self.root), str(self.root))['total'], 1)

    def test_powershell_is_counted_as_code(self):
        (self.root / 'guard.ps1').write_text('exit 2\n')
        entries = inventory.count_lines(inventory.walk(str(self.root)))
        item = next(e for e in entries if e['rel'] == 'guard.ps1')
        self.assertEqual((item['kind'], item['lines']), ('code', 1))

    def test_inventory_default_never_launches_external_tools(self):
        with patch.object(sys, 'argv', ['inventory', str(self.root)]), patch.object(inventory, 'run') as runner:
            inventory.main()
        runner.assert_not_called()
        self.assertIn('SKIP: not requested', (self.root / '.inventory/02_findings.json').read_text(encoding='utf-8'))

    def test_invalid_edl_rejected(self):
        for edl in ([], [{'clip': 'a', 'dur_seconds': -1}], [{'clip': 'a', 'dur_seconds': 'nan'}], [{'dur_seconds': 1}]):
            with self.subTest(edl=edl), self.assertRaises(SystemExit): video.validate_edl(edl)

    def test_ambiguous_or_traversing_clip_rejected(self):
        (self.root / 'clip.mov').write_text('a')
        (self.root / 'clip.mp4').write_text('a')
        for clip in ('clip', '../outside', '*'):
            with self.assertRaises(SystemExit): video.clip_files(self.root, clip)

    def test_existing_video_output_is_preserved(self):
        out = self.root / 'result.mp4'; out.write_text('keep')
        with patch.dict(os.environ, {'VIDEO_OUTPUT': str(out)}):
            with self.assertRaises(SystemExit): video.output_file()
        self.assertEqual(out.read_text(), 'keep')

    def test_media_recipes_require_explicit_work_directory(self):
        env = {k: v for k, v in os.environ.items() if k not in ('VIDEO_WORK', 'VIDEO_SOURCE', 'VIDEO_OUTPUT')}
        for name in ('build_edit.py', 'build_edit2.py', 'build_edit3.py', 'parse_edl.py'):
            p = subprocess.run([sys.executable, str(ROOT / 'skills/video-montage/scripts' / name)], env=env, capture_output=True)
            self.assertNotEqual(p.returncode, 0, name)
            self.assertIn(b'VIDEO_WORK', p.stderr)

    def csv(self, name, rows):
        path = self.root / name
        with path.open('w', encoding='utf-8', newline='') as f: csv.writer(f).writerows(rows)
        return path

    def merge(self, out, *inputs):
        return subprocess.run([sys.executable, str(ROOT / 'skills/geo-lead-parser/scripts/merge_normalize.py'), str(out), *map(str, inputs)], capture_output=True)

    def test_csv_reordered_columns_align(self):
        a = self.csv('a.csv', [['name', 'phone'], ['First', '89001234567']])
        b = self.csv('b.csv', [['phone', 'name'], ['89007654321', 'Second']])
        out = self.root / 'out.csv'
        self.assertEqual(self.merge(out, a, b).returncode, 0)
        with out.open(encoding='utf-8-sig', newline='') as f: rows = list(csv.reader(f))
        self.assertEqual(rows[2], ['Second', '+79007654321'])

    def test_csv_incompatible_schema_rejected_without_output(self):
        a = self.csv('a.csv', [['name', 'phone'], ['A', '89001234567']])
        b = self.csv('b.csv', [['name', 'email'], ['B', 'b@example.invalid']])
        out = self.root / 'out.csv'
        self.assertNotEqual(self.merge(out, a, b).returncode, 0)
        self.assertFalse(out.exists())

    def test_csv_missing_input_is_failure(self):
        self.assertNotEqual(self.merge(self.root / 'out.csv', self.root / 'missing.csv').returncode, 0)

    def test_csv_cannot_overwrite_input(self):
        source = self.csv('source.csv', [['name'], ['A']])
        before = source.read_bytes()
        self.assertNotEqual(self.merge(source, source).returncode, 0)
        self.assertEqual(source.read_bytes(), before)

if __name__ == '__main__': unittest.main()

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/acceptance-gate/checks.py'
spec = importlib.util.spec_from_file_location('acceptance_checks', SCRIPT)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

RUN = '''---
run_id: synthetic
status: done
obraz_gotovogo: filled
artifacts: ["result.json"]
---
## Образ готового
- Образец: fixture
- Получатель, канал, устройство: reviewer, file, desktop
- Уровень: рабочий
- Чем проверим: JSON parser
## Бюджеты
| Модель | Токены |
| local-test | 0 |
## Trace
Test executed
'''


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run.md'
        (self.root / 'result.json').write_text('{"ok":true}', encoding='utf-8')

    def run_cli(self, content=RUN, cwd=None):
        self.run.write_text(content, encoding='utf-8')
        return subprocess.run([sys.executable, str(SCRIPT), str(self.run), '--json'],
                              env=dict(os.environ, VAULT_ROOT=str(self.root / 'vault'), CLAUDE_HOME=str(self.root / 'stack')),
                              cwd=cwd, capture_output=True, encoding='utf-8', timeout=20)

    def test_valid_run(self):
        p = self.run_cli()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_missing_relative_artifact_fails(self):
        self.assertEqual(self.run_cli(RUN.replace('result.json', 'missing.json')).returncode, 1)

    def test_cwd_cannot_supply_missing_artifact(self):
        other = self.root / 'unrelated'; other.mkdir()
        (other / 'missing.json').write_text('{}')
        self.assertEqual(self.run_cli(RUN.replace('result.json', 'missing.json'), other).returncode, 1)

    def test_corrupt_artifact_fails(self):
        (self.root / 'result.json').write_text('broken')
        self.assertEqual(self.run_cli().returncode, 1)

    def test_duplicate_status_is_invalid(self):
        self.assertEqual(self.run_cli(RUN.replace('status: done', 'status: done\nstatus: planning')).returncode, 2)

    def test_quoted_status_with_comment(self):
        self.assertEqual(self.run_cli(RUN.replace('status: done', 'status: "done" # closed')).returncode, 0)

    def test_planning_is_ineligible(self):
        self.assertEqual(self.run_cli(RUN.replace('status: done', 'status: planning')).returncode, 4)

    def test_placeholder_field_fails(self):
        self.assertEqual(self.run_cli(RUN.replace('Уровень: рабочий', 'Уровень: TODO')).returncode, 1)

    def test_label_without_value_fails(self):
        self.assertEqual(self.run_cli(RUN.replace('Образец: fixture', 'Образец')).returncode, 1)

    def test_higher_heading_ends_obraz(self):
        self.assertEqual(self.run_cli(RUN.replace('- Уровень:', '# Another section\n- Уровень:')).returncode, 1)

    def test_quoted_comma_in_path(self):
        (self.root / 'result, 1.json').write_text('{}')
        self.assertEqual(self.run_cli(RUN.replace('result.json', 'result, 1.json')).returncode, 0)

    def test_block_artifacts(self):
        self.assertEqual(self.run_cli(RUN.replace('artifacts: ["result.json"]', 'artifacts:\n  - "result.json"')).returncode, 0)

    def test_duplicate_artifacts_rejected(self):
        self.assertEqual(self.run_cli(RUN.replace('artifacts:', 'artifacts: []\nartifacts:')).returncode, 2)

    def test_pdf_signature_is_not_opening_proof(self):
        p = self.root / 'fake.pdf'; p.write_bytes(b'%PDF-1.7\nnot a document')
        self.assertEqual(checks.artifact_opens(str(p))[0], checks.SKIP)

    def test_fake_office_fails(self):
        p = self.root / 'fake.docx'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
        self.assertEqual(checks.artifact_opens(str(p))[0], checks.FAIL)

    def test_invalid_utf8_fails(self):
        p = self.root / 'bad.md'; p.write_bytes(b'\xff\xfeinvalid')
        self.assertEqual(checks.artifact_opens(str(p))[0], checks.FAIL)

    def test_missing_run_is_error(self):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.root / 'no.md')], capture_output=True)
        self.assertEqual(p.returncode, 2)


if __name__ == '__main__':
    unittest.main()

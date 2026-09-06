import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import doctor
import install


class DoctorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='orchestrator-doctor-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'stack'
        install.install(self.root, Path(temp.name) / 'vault', 'minimal', True)

    def checks(self):
        return {item['check']: item for item in doctor.inspect(self.root, installed=True)}

    def change_hook(self, key, value):
        path = self.root / 'settings.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        entry = cfg['hooks']['PreToolUse'][0]
        if key == 'matcher': entry[key] = value
        else: entry['hooks'][0][key] = value
        path.write_text(json.dumps(cfg), encoding='utf-8')

    def test_real_installed_guards_pass_wiring_and_smoke(self):
        checks = self.checks()
        for key in ('secret-guard-wiring', 'risk-guard-wiring', 'guard-smoke'):
            self.assertEqual(checks[key]['status'], 'pass', checks)

    def test_missing_guard_fails_wiring_and_smoke(self):
        (self.root / 'tools/guard.py').unlink()
        checks = self.checks()
        self.assertEqual(checks['secret-guard-wiring']['status'], 'fail')
        self.assertEqual(checks['guard-smoke']['status'], 'fail')

    def test_read_matcher_does_not_protect_writes(self):
        self.change_hook('matcher', 'Read')
        self.assertEqual(self.checks()['secret-guard-wiring']['status'], 'fail')

    def test_wrong_interpreter_fails_wiring(self):
        self.change_hook('command', 'nonexistent-orchestrator-python')
        self.assertEqual(self.checks()['secret-guard-wiring']['status'], 'fail')

    def test_guard_crash_is_not_accepted_as_a_block(self):
        (self.root / 'tools/guard.py').write_text('raise RuntimeError("synthetic crash")\n', encoding='utf-8')
        self.assertEqual(self.checks()['guard-smoke']['status'], 'fail')

    def test_guard_timeout_is_an_explicit_failed_diagnostic(self):
        original = subprocess.run
        def run(args, **kwargs):
            if len(args) > 1 and args[1] == str(self.root / 'tools/guard.py'):
                raise subprocess.TimeoutExpired(args, kwargs['timeout'])
            return original(args, **kwargs)
        with mock.patch.object(doctor.subprocess, 'run', side_effect=run):
            check = self.checks()['guard-smoke']
        self.assertEqual(check['status'], 'fail')
        self.assertIn('timed out', check['detail'])


if __name__ == '__main__':
    unittest.main()

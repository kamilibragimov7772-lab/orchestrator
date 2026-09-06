import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import guard
import secret_scan


class GuardTests(unittest.TestCase):
    def test_multiple_credential_families(self):
        samples = [('openai', 'sk-' + 'proj-' + 'a' * 40), ('github', 'ghp_' + 'a' * 36),
                   ('gitlab', 'glpat-' + 'a' * 22), ('aws', 'AKIA' + 'A' * 16),
                   ('google', 'AIza' + 'a' * 35), ('stripe', 'sk_live_' + 'a' * 30),
                   ('huggingface', 'hf_' + 'a' * 32), ('slack', 'xoxb-' + 'a' * 24)]
        for kind, token in samples:
            with self.subTest(kind=kind): self.assertIn(kind, secret_scan.detect(token))

    def test_safe_placeholder(self):
        self.assertEqual(secret_scan.detect('OPENAI_API_KEY=<your-key>'), [])

    def test_edit_scans_new_content_only(self):
        evt = {'tool_name': 'Edit', 'tool_input': {'old_string': 'sk-' + 'A' * 40, 'new_string': '<redacted>'}}
        self.assertIsNone(guard.evaluate('secret', evt))

    def test_force_push_and_echo_differ(self):
        self.assertIsNotNone(guard.risky('git push --force origin main'))
        self.assertIsNone(guard.risky('echo "git push --force origin main"'))

    def test_command_after_echo(self):
        self.assertIsNotNone(guard.risky('echo "safe"; git push -f origin main'))

    def test_substitution_inside_echo_is_not_stripped(self):
        self.assertIsNotNone(guard.risky('echo "$(git push --force origin main)"'))

    def test_quote_concatenation(self):
        self.assertIsNotNone(guard.risky('g""it push --force origin main'))

    def test_reordered_delete_flags(self):
        self.assertIsNotNone(guard.risky('Remove-Item -Force C:/example -Recurse'))
        self.assertIsNotNone(guard.risky('rm -fr /example'))

    def test_http_data_is_a_write(self):
        self.assertIsNotNone(guard.risky('curl --data x=1 https://example.invalid'))
        self.assertIsNone(guard.risky('curl https://example.invalid'))

    def test_invalid_json_fails_closed_without_echo(self):
        p = subprocess.run([sys.executable, str(ROOT / 'tools/guard.py'), 'secret'], input='PRIVATE_INPUT',
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('PRIVATE_INPUT', p.stderr)

    def test_json_escaping_is_decoded(self):
        event = {'tool_name': 'Write', 'tool_input': {'file_path': 'note.md', 'content': 'sk-' + 'proj-' + 'Z' * 40}}
        payload = json.dumps(event).replace('sk-', '\\u0073k-')
        p = subprocess.run([sys.executable, str(ROOT / 'tools/guard.py'), 'secret'], input=payload,
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('Z' * 40, p.stderr)

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell unavailable')
    def test_powershell_wrapper_reads_stdin(self):
        event = {'tool_name': 'Bash', 'tool_input': {'command': 'git push --force origin main'}}
        for exe in {shutil.which('pwsh'), shutil.which('powershell')} - {None}:
            with self.subTest(exe=exe):
                p = subprocess.run([exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'hooks/risk-guard.ps1')],
                                   input=json.dumps(event), text=True, capture_output=True,
                                   env=dict(os.environ, ORCHESTRATOR_PYTHON=sys.executable), timeout=20)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)



if __name__ == '__main__':
    unittest.main()

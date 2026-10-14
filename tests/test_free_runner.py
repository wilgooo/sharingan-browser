"""Host-safe CI tests: never download source, remove tools, or invoke sudo."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ci/free_runner.py'
spec = importlib.util.spec_from_file_location('free_runner', SCRIPT)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.logs = self.root / 'logs'
        self.logs.mkdir()
        event = self.root / 'event.json'
        event.write_text(json.dumps({'repository': {'private': False}}))
        self.env = {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                    'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64', 'GITHUB_EVENT_PATH': str(event)}

    def guard(self):
        ci.require_disposable_runner(self.env, 'Linux', 'x86_64')

    def test_public_disposable_linux_allowed(self):
        self.guard()

    def test_local_machine_rejected(self):
        self.env.pop('GITHUB_ACTIONS')
        with self.assertRaisesRegex(RuntimeError, 'disposable'):
            self.guard()

    def test_self_hosted_rejected(self):
        self.env['RUNNER_ENVIRONMENT'] = 'self-hosted'
        with self.assertRaisesRegex(RuntimeError, 'disposable'):
            self.guard()

    def test_private_repository_rejected(self):
        Path(self.env['GITHUB_EVENT_PATH']).write_text(json.dumps({'repository': {'private': True}}))
        with self.assertRaisesRegex(RuntimeError, 'public repositories'):
            self.guard()

    def test_missing_visibility_rejected(self):
        Path(self.env['GITHUB_EVENT_PATH']).write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'public repositories'):
            self.guard()

    def test_arm_builder_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'x86-64'):
            ci.require_disposable_runner(self.env, 'Linux', 'aarch64')

    def test_low_disk_rejected(self):
        with mock.patch.object(ci.shutil, 'disk_usage', return_value=mock.Mock(free=2 * ci.GIB)):
            with self.assertRaisesRegex(RuntimeError, 'Disk gate'):
                ci.require_space(self.root, 3)

    def test_process_success_and_logs(self):
        runner = ci.Runner(self.root, self.logs)
        with mock.patch.object(ci, 'require_space'), contextlib.redirect_stdout(io.StringIO()):
            runner.run('success', [sys.executable, '-c', 'print("hello")'])
        self.assertEqual(runner.state['stages'][0]['status'], 'passed')
        self.assertIn('hello', (self.logs / 'success.log').read_text())

    def test_failed_process_saves_status_and_output(self):
        runner = ci.Runner(self.root, self.logs)
        with mock.patch.object(ci, 'require_space'), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'exit 7'):
                runner.run('failure', [sys.executable, '-c', 'print("expected failure"); raise SystemExit(7)'])
        saved = json.loads((self.logs / 'status.json').read_text())
        self.assertEqual(saved['stages'][0]['status'], 'failed')
        self.assertIn('expected failure', (self.logs / 'failure.log').read_text())

    def test_deadline_stops_process_and_records_timeout(self):
        runner = ci.Runner(self.root, self.logs, budget_seconds=0.2)
        with mock.patch.object(ci, 'require_space'), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'timeout'):
                runner.run('timeout', [sys.executable, '-c', 'import time; time.sleep(60)'])
        self.assertEqual(runner.state['stages'][0]['status'], 'failed')

if __name__ == '__main__':
    unittest.main()

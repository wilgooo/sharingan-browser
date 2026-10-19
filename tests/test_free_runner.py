"""Host-safe CI tests: never download source, remove tools, or invoke sudo."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
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

    def test_network_retries_transient_failure_and_keeps_attempt_logs(self):
        runner = ci.Runner(self.root, self.logs)
        calls = []
        def fail_once(name, command, **kwargs):
            calls.append(name)
            if len(calls) == 1:
                (self.logs / f'{name}.log').write_text('RPC failed; HTTP 503 curl 22')
                raise ci.CommandFailed('exit 128')
        with mock.patch.object(runner, 'run', side_effect=fail_once), mock.patch.object(ci.time, 'sleep'):
            runner.network('fetch', ['git', 'fetch'])
        self.assertEqual(calls, ['fetch-attempt-1', 'fetch-attempt-2'])
        self.assertTrue((self.logs / 'fetch-attempt-1.log').exists())

    def test_network_retry_is_bounded(self):
        runner = ci.Runner(self.root, self.logs)
        def fail(name, command, **kwargs):
            (self.logs / f'{name}.log').write_text('returned error: 503')
            raise ci.CommandFailed('exit 128')
        with mock.patch.object(runner, 'run', side_effect=fail) as run, mock.patch.object(ci.time, 'sleep'):
            with self.assertRaises(ci.CommandFailed):
                runner.network('fetch', ['git', 'fetch'])
        self.assertEqual(run.call_count, 3)

    def test_network_does_not_retry_permanent_or_resource_errors(self):
        runner = ci.Runner(self.root, self.logs)
        (self.logs / 'fetch-attempt-1.log').write_text('fatal: could not find remote ref invalid')
        for error in (ci.CommandFailed('exit 128'), RuntimeError('Disk gate'), RuntimeError('timeout')):
            with self.subTest(error=str(error)), mock.patch.object(runner, 'run', side_effect=error) as run:
                with self.assertRaises(RuntimeError):
                    runner.network('fetch', ['git', 'fetch'])
                self.assertEqual(run.call_count, 1)

    def test_checkout_retains_requested_tag_and_origin(self):
        source = self.root / 'source'
        source.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(source), *args], stderr=subprocess.DEVNULL, text=True).strip()
        git('init')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '--allow-empty', '-m', 'fixture')
        git('tag', 'test-version')
        target = self.root / 'checkout'
        runner = ci.Runner(self.root, self.logs)
        with mock.patch.object(ci, 'require_space'), contextlib.redirect_stdout(io.StringIO()):
            runner.checkout('fixture', source.as_uri(), 'refs/tags/test-version', target, minutes=1)
        head = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'refs/tags/test-version^{commit}'], text=True).strip()
        self.assertEqual(head, git('rev-parse', 'HEAD'))
        origin = subprocess.check_output(['git', '-C', str(target), 'remote', 'get-url', 'origin'], text=True).strip()
        self.assertEqual(origin, source.as_uri())

class InstallScriptTests(unittest.TestCase):
    SNAP = 'if package_exists snapcraft; then\n    dev_list="${dev_list} snapcraft"\nfi\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'src/build').mkdir(parents=True)
        (self.root / 'src/build/install-build-deps-android.sh').write_text('#!/bin/bash\necho android\n')

    def write_main(self, body):
        (self.root / 'src/build/install-build-deps.sh').write_text(body)

    def test_staged_installer_drops_snapcraft_and_keeps_source_clean(self):
        original = 'before\n' + self.SNAP + 'after\n'
        self.write_main(original)
        android = ci.stage_install_scripts(self.root / 'src', self.root / 'staged')
        self.assertEqual(android.name, 'install-build-deps-android.sh')
        staged = (android.parent / 'install-build-deps.sh').read_text()
        self.assertNotIn('snapcraft', staged)
        self.assertIn('before', staged)
        self.assertIn('after', staged)
        self.assertEqual((self.root / 'src/build/install-build-deps.sh').read_text(), original)

    def test_staged_installer_fails_loudly_when_upstream_changes(self):
        self.write_main('no snap block here\n')
        with self.assertRaises(RuntimeError):
            ci.stage_install_scripts(self.root / 'src', self.root / 'staged')


class ModeTests(unittest.TestCase):
    WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/android-free.yml'

    def test_gn_only_mode_is_accepted(self):
        self.assertEqual(ci.parse_args(['--mode', 'gn-only']).mode, 'gn-only')
        self.assertEqual(ci.parse_args([]).mode, 'build')

    def test_unknown_mode_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ci.parse_args(['--mode', 'compile-only'])

    def test_only_build_mode_compiles(self):
        self.assertFalse(ci.compiles('gn-only'))
        self.assertFalse(ci.compiles('preflight'))
        self.assertTrue(ci.compiles('build'))

    def test_workflow_offers_gn_only_and_keeps_apk_upload_build_only(self):
        text = self.WORKFLOW.read_text()
        self.assertIn('options: [build, gn-only, preflight]', text)
        self.assertIn("inputs.mode != 'preflight' && steps.apt-cache", text)
        self.assertIn("if: ${{ success() && inputs.mode == 'build' }}", text)

if __name__ == '__main__':
    unittest.main()

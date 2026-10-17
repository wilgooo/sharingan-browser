"""Exercise checkout protection and repeatability using tiny local Git repos."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare.py'
spec = importlib.util.spec_from_file_location('prepare', SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.bundle = root / 'bundle'
        self.src = root / 'src'
        self.src.mkdir()
        (self.bundle / 'config').mkdir(parents=True)
        (self.bundle / 'chromium-overlay/chrome').mkdir(parents=True)
        (self.bundle / 'chromium-overlay/chrome/test.txt').write_text('Sharingan')
        self.digest = hashlib.sha256(b'Sharingan').hexdigest()
        (self.bundle / 'config/overlay.sha256.json').write_text(json.dumps({'chrome/test.txt': self.digest}))
        (self.bundle / 'config/upstream.lock.json').write_text(json.dumps({'chromium_version_candidate': '132.0.6834.83'}))
        (self.bundle / 'config/args.gn').write_text('target_os = "android"\n')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Local Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.src / 'chrome').mkdir()
        (self.src / 'chrome/test.txt').write_text('Chromium')
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture')
        self.git('tag', '132.0.6834.83')
        prepare.ROOT = self.bundle

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.src), *args], stderr=subprocess.STDOUT)

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            prepare.prepare(self.src)

    def test_applies_and_is_repeatable(self):
        self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'Sharingan')
        self.apply()
        self.assertTrue((self.src / '.sharingan-source.json').is_file())

    def test_wrong_revision_rejected(self):
        (self.src / 'extra').write_text('new commit')
        self.git('add', '.')
        self.git('commit', '-qm', 'Another revision')
        with self.assertRaisesRegex(RuntimeError, 'Expected Chromium tag'):
            self.apply()

    def test_dirty_checkout_preserved(self):
        (self.src / 'chrome/test.txt').write_text('User edit')
        with self.assertRaisesRegex(RuntimeError, 'local changes'):
            self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'User edit')

    def test_matching_tag_with_unexpected_commit_rejected(self):
        lock_path = self.bundle / 'config/upstream.lock.json'
        lock = json.loads(lock_path.read_text())
        lock['chromium_commit'] = '0' * 40
        lock_path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(RuntimeError, 'audited baseline'):
            self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'Chromium')

    def test_tampered_bundle_rejected_before_write(self):
        (self.bundle / 'chromium-overlay/chrome/test.txt').write_text('Tampered')
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'Chromium')

    def test_existing_build_args_preserved(self):
        out = self.src / 'out/sharingan_arm64'
        out.mkdir(parents=True)
        (out / 'args.gn').write_text('User settings')
        with self.assertRaisesRegex(RuntimeError, 'Existing Sharingan build args'):
            self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'Chromium')

    def test_edits_after_preparation_preserved(self):
        self.apply()
        (self.src / 'chrome/test.txt').write_text('User edit')
        with self.assertRaisesRegex(RuntimeError, 'Prepared source changed'):
            self.apply()
        self.assertEqual((self.src / 'chrome/test.txt').read_text(), 'User edit')

    def test_untracked_destination_preserved(self):
        (self.bundle / 'chromium-overlay/chrome/new.txt').write_text('Sharingan')
        (self.bundle / 'config/overlay.sha256.json').write_text(json.dumps({'chrome/new.txt': self.digest}))
        (self.src / 'chrome/new.txt').write_text('User file')
        with self.assertRaisesRegex(RuntimeError, 'Untracked file'):
            self.apply()

    def test_path_traversal_rejected(self):
        # An altered manifest must never write outside the chosen checkout.
        (self.bundle / 'escaped.txt').write_text('Sharingan')
        (self.bundle / 'config/overlay.sha256.json').write_text(json.dumps({'../escaped.txt': self.digest}))
        with self.assertRaisesRegex(RuntimeError, 'escapes checkout'):
            self.apply()
        self.assertFalse((self.src.parent / 'escaped.txt').exists())

if __name__ == '__main__':
    unittest.main()

"""Host-safe tests for carrying ninja output between chained CI jobs."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ci/build_resume.py'
spec = importlib.util.spec_from_file_location('build_resume', SCRIPT)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)

# zstd is the CI compressor; gzip keeps the round trip testable on any host tar.
COMPRESSOR = 'gzip'


class OverlayStateTests(unittest.TestCase):
    def test_changed_files_include_edits_additions_and_removals(self):
        previous = {'same.h': 'a', 'edited.h': 'b', 'dropped.h': 'c'}
        current = {'same.h': 'a', 'edited.h': 'B', 'added.h': 'd'}
        self.assertEqual(resume.changed_overlay_files(previous, current),
                         ['added.h', 'dropped.h', 'edited.h'])

    def test_complete_compile_matches_current_overlay(self):
        current = {'edited.h': 'B'}
        self.assertEqual(resume.consistent_overlay({'edited.h': 'b'}, current, complete=True), current)

    def test_fresh_build_matches_current_overlay(self):
        current = {'edited.h': 'B'}
        self.assertEqual(resume.consistent_overlay(None, current, complete=False), current)

    def test_incomplete_compile_keeps_changed_files_stale_for_the_next_job(self):
        previous = {'same.h': 'a', 'edited.h': 'b', 'dropped.h': 'c'}
        current = {'same.h': 'a', 'edited.h': 'B', 'added.h': 'd'}
        state = resume.consistent_overlay(previous, current, complete=False)
        self.assertEqual(state, {'same.h': 'a', 'edited.h': 'b', 'dropped.h': 'c'})
        # The next job therefore bumps every one of them again.
        self.assertEqual(resume.changed_overlay_files(state, current),
                         ['added.h', 'dropped.h', 'edited.h'])


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'
        (self.root / 'config').mkdir(parents=True)
        (self.root / 'config/upstream.lock.json').write_text('{"commit": "x"}\n')
        (self.root / 'config/args.free.gn').write_text('target_os = "android"\n')
        self.src = self.base / 'src'
        (self.src / 'chrome').mkdir(parents=True)
        (self.src / 'chrome/a.h').write_text('a')
        (self.src / 'chrome/b.h').write_text('b')
        (self.src / '.git').mkdir()
        (self.src / '.git/HEAD').write_text('ref')
        self.out = self.src / 'out/sharingan_arm64'
        self.out.mkdir(parents=True)
        (self.out / 'obj.o').write_text('object')
        self.archive = self.base / 'cache/out.tar.zst'

    def test_pinning_skips_outputs_and_git_and_never_follows_symlinks(self):
        target = self.base / 'outside.txt'
        target.write_text('outside')
        os.symlink(target, self.src / 'chrome/link.h')
        resume.pin_source_mtimes(self.src)
        self.assertEqual((self.src / 'chrome/a.h').stat().st_mtime, resume.SOURCE_EPOCH)
        self.assertNotEqual((self.out / 'obj.o').stat().st_mtime, resume.SOURCE_EPOCH)
        self.assertNotEqual((self.src / '.git/HEAD').stat().st_mtime, resume.SOURCE_EPOCH)
        self.assertNotEqual(target.stat().st_mtime, resume.SOURCE_EPOCH)

    def test_round_trip_rebuilds_only_changed_overlay_files(self):
        previous = {'chrome/a.h': 'old-a', 'chrome/b.h': 'b'}
        current = {'chrome/a.h': 'new-a', 'chrome/b.h': 'b'}
        os.utime(self.out / 'obj.o', (2_000_000_000.5, 2_000_000_000.5))
        resume.stash(self.out, self.archive, self.root, previous, None, complete=True,
                     compressor=COMPRESSOR)
        (self.out / 'obj.o').unlink()
        restored = resume.restore(self.src, self.out, self.archive, self.root, current,
                                  compressor=COMPRESSOR)
        self.assertEqual(restored, previous)
        self.assertFalse(self.archive.exists())
        self.assertEqual((self.out / 'obj.o').read_text(), 'object')
        # Sub-second output mtimes survive, so ninja's log comparison still matches.
        self.assertEqual((self.out / 'obj.o').stat().st_mtime, 2_000_000_000.5)
        self.assertEqual((self.src / 'chrome/b.h').stat().st_mtime, resume.SOURCE_EPOCH)
        self.assertGreater((self.src / 'chrome/a.h').stat().st_mtime, resume.SOURCE_EPOCH)

    def test_changed_build_args_discard_saved_outputs(self):
        resume.stash(self.out, self.archive, self.root, {}, None, complete=True, compressor=COMPRESSOR)
        (self.root / 'config/args.free.gn').write_text('target_os = "android"\nis_debug = true\n')
        self.assertIsNone(resume.restore(self.src, self.out, self.archive, self.root, {},
                                         compressor=COMPRESSOR))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_corrupt_archive_falls_back_to_clean_build(self):
        self.archive.parent.mkdir(parents=True)
        self.archive.write_bytes(b'not an archive')
        self.assertIsNone(resume.restore(self.src, self.out, self.archive, self.root, {},
                                         compressor=COMPRESSOR))
        self.assertFalse(self.archive.exists())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_missing_archive_means_clean_build(self):
        self.assertIsNone(resume.restore(self.src, self.out, self.archive, self.root, {}))
        self.assertTrue((self.out / 'obj.o').exists())

    def test_marker_records_the_consistent_overlay(self):
        resume.stash(self.out, self.archive, self.root, {'chrome/a.h': 'new'},
                     {'chrome/a.h': 'old'}, complete=False, compressor=COMPRESSOR)
        marker = json.loads((self.out / resume.MARKER).read_text())
        self.assertEqual(marker['overlay'], {'chrome/a.h': 'old'})
        self.assertEqual(marker['fingerprint'], resume.fingerprint(self.root))


if __name__ == '__main__':
    unittest.main()

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_cache', ROOT / 'scripts/ci/package_cache.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)

class PackageCacheTests(unittest.TestCase):
    def test_export_is_bounded_and_ignores_partial_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archives, dest = root / 'archives', root / 'cache'
            archives.mkdir()
            (archives / 'good.deb').write_bytes(b'good')
            (archives / 'large.deb').write_bytes(b'large-package')
            (archives / 'partial').mkdir()
            (archives / 'partial/download.deb').write_bytes(b'partial')
            (archives / 'link.deb').symlink_to(archives / 'good.deb')
            result = cache.export_packages(archives, dest, limit=5)
            self.assertEqual(result['bytes'], 4)
            self.assertEqual(sorted(p.name for p in dest.iterdir()), ['.ready', 'good.deb'])

    def test_empty_export_cannot_save_old_ready_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archives, dest = root / 'archives', root / 'cache'
            archives.mkdir(); dest.mkdir()
            (dest / '.ready').write_text('stale')
            (dest / 'stale.deb').write_bytes(b'stale')
            cache.export_packages(archives, dest)
            self.assertEqual(list(dest.iterdir()), [])

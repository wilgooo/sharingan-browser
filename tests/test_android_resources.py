import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resources', ROOT / 'scripts/check_android_resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)

class ResourceInputsTest(unittest.TestCase):
    def test_complete_overlay(self):
        self.assertEqual(resources.check(ROOT), [])

    def test_missing_component_input_and_invalid_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir()
            (root / 'config/chromium_android_resource_paths.json').write_text('[]')
            folder = root / 'chromium-overlay/components/widget'
            (folder / 'java/res/layout').mkdir(parents=True)
            (folder / 'BUILD.gn').write_text('sources = [ "java/res/layout/missing.xml" ]')
            (folder / 'java/res/layout/broken.xml').write_text('<resources>')
            errors = resources.check(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any('missing.xml' in error for error in errors))
            self.assertTrue(any('invalid XML' in error for error in errors))

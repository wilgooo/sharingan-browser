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

    def test_base_module_overlay_icons_are_declared(self):
        android = ROOT / 'chromium-overlay/chrome/android'
        target = (android / 'BUILD.gn').read_text().split('android_resources("chrome_base_module_resources")', 1)[1].split('\n}', 1)[0]
        for path in (android / 'java/res_chromium_base').rglob('*'):
            if path.suffix in ('.png', '.xml'):
                self.assertIn('"' + path.relative_to(android).as_posix() + '"', target)

    def test_app_overlay_resources_are_declared(self):
        import re
        android = ROOT / 'chromium-overlay/chrome/android'
        text = (android / 'chrome_java_resources.gni').read_text()
        declared = {v.removeprefix('//chrome/android/') for v in re.findall('"([^"\n]+)"', text)}
        for path in (android / 'java/res').rglob('*'):
            if path.is_file() and path.suffix in ('.xml', '.png', '.webp', '.jpg'):
                self.assertIn(path.relative_to(android).as_posix(), declared)

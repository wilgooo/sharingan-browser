import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_audit', ROOT / 'scripts/check_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditGateTest(unittest.TestCase):
    def test_android_excludes_desktop_but_keeps_extension_resources(self):
        text = (ROOT / 'chromium-overlay/chrome/chrome_paks.gni').read_text()
        reachable = audit.reachable_strings(text)
        self.assertIn('//chrome/browser/resources/extensions:resources', reachable)
        self.assertIn('//chrome/browser/resources:component_extension_resources', reachable)
        self.assertNotIn('//chrome/browser/resources/settings:resources', reachable)
        self.assertNotIn('$root_gen_dir/chrome/settings_resources.pak', reachable)

    def test_regression_old_bypass_exposes_both_pak_and_dependency(self):
        text = (ROOT / 'chromium-overlay/chrome/chrome_paks.gni').read_text()
        text = text.replace('if (!is_android)', 'if (!is_android || true)')
        reachable = audit.reachable_strings(text)
        self.assertIn('//chrome/browser/resources/settings:resources', reachable)
        self.assertIn('$root_gen_dir/chrome/settings_resources.pak', reachable)

    def test_unknown_guard_is_not_proof_of_exclusion(self):
        self.assertIn('//desktop', audit.reachable_strings('if (unknown_flag) { deps = [ "//desktop" ] }'))
        self.assertNotIn('//desktop', audit.reachable_strings('if (!is_android && unknown_flag) { deps = [ "//desktop" ] }'))

    def test_comments_and_strings_do_not_change_scope(self):
        self.assertEqual(audit.reachable_strings('# if (false) {\n group("}") { deps = [ "//needed" ] }'), ['}', '//needed'])

    def test_else_branch_and_desktop_preservation(self):
        text = 'if (is_android) { deps = [ "android" ] } else { deps = [ "desktop" ] }'
        self.assertEqual(audit.reachable_strings(text), ['android'])
        self.assertEqual(audit.reachable_strings(text, {'is_android': False}), ['desktop'])

    def test_modal_core_enabled_without_desktop_tests_on_android(self):
        text = (ROOT / 'chromium-overlay/components/web_modal/BUILD.gn').read_text()
        reachable = audit.reachable_strings(text)
        self.assertIn('web_modal', reachable)
        self.assertNotIn('unit_tests', reachable)
        self.assertNotIn('test_support', reachable)
        self.assertNotIn('//content/test:test_support', reachable)
        self.assertFalse(audit.condition('!is_ios && (!is_android || enable_extensions)',
                                        dict(audit.ANDROID, enable_extensions=False)))

    def test_renderer_keeps_android_searchbox_without_desktop_accessibility(self):
        text = (ROOT / 'chromium-overlay/chrome/renderer/BUILD.gn').read_text()
        reachable = audit.reachable_strings(text)
        self.assertIn('searchbox/searchbox.cc', reachable)
        self.assertNotIn('//chrome/common/accessibility:mojo_bindings', reachable)
        regressed = text.replace('if (!is_android)', 'if (!is_android || is_android)')
        self.assertIn('//chrome/common/accessibility:mojo_bindings',
                      audit.reachable_strings(regressed))

    def test_known_blockers_are_closed(self):
        self.assertEqual(audit.check(), [])


if __name__ == '__main__':
    unittest.main()

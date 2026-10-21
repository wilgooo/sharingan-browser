import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_audit', ROOT / 'scripts/check_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditGateTest(unittest.TestCase):
    def test_android_resource_list_has_all_inputs(self):
        import json
        import re
        inherited = set(json.loads((ROOT / 'config/chromium_android_resource_paths.json').read_text()))
        overlay = ROOT / 'chromium-overlay'
        text = (overlay / 'chrome/android/chrome_java_resources.gni').read_text()
        for item in re.findall(r'"((?://chrome/android/)?java/res/[^"$]+)"', text):
            rel = item[2:] if item.startswith('//') else 'chrome/android/' + item
            self.assertTrue((overlay / rel).is_file() or rel in inherited, rel)

    def test_android_focus_module_has_producer_and_definition(self):
        root = ROOT / 'chromium-overlay/ui/webui/resources'
        self.assertIn('js/cr/ui/focus_without_ink.m.js', audit.reachable_strings((root / 'BUILD.gn').read_text()))
        producer = (root / 'js/cr/ui/BUILD.gn').read_text().split('preprocess_if_expr("preprocess_generated")', 1)[1].split('\ngenerate_grd(', 1)[0]
        self.assertIn('focus_without_ink.m.js', audit.reachable_strings(producer))

    def test_shortcut_consumers_use_generated_module(self):
        for name in ['BUILD.gn', 'cr_elements/find_shortcut_behavior.js',
                     'cr_elements/find_shortcut_mixin.ts']:
            text = (ROOT / 'chromium-overlay/ui/webui/resources' / name).read_text()
            self.assertIn('js/cr/ui/keyboard_shortcut_list.m.js', text)
            self.assertNotIn('js/cr/ui/keyboard_shortcut_list.js', text)

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

    def test_service_discovery_dependency_tracks_its_consumer(self):
        text = (ROOT / 'chromium-overlay/chrome/browser/extensions/BUILD.gn').read_text()
        for enabled in (False, True):
            reachable = audit.reachable_strings(
                text, dict(audit.ANDROID, enable_service_discovery=enabled))
            self.assertEqual('api/mdns/mdns_api.cc' in reachable, enabled)
            self.assertEqual('//chrome/browser/media/router/discovery' in reachable, enabled)

    def test_platform_apps_discovery_remains_desktop_only(self):
        text = (ROOT / 'chromium-overlay/chrome/browser/apps/platform_apps/BUILD.gn').read_text()
        label = '//chrome/browser/media/router/discovery'
        self.assertNotIn(label, audit.reachable_strings(text))
        self.assertIn(label, audit.reachable_strings(text, dict(audit.ANDROID, is_android=False)))

    def test_extension_ui_separates_views_from_android_core(self):
        text = (ROOT / 'chromium-overlay/chrome/browser/ui/BUILD.gn').read_text()
        android = audit.reachable_strings(text)
        self.assertIn('//extensions/browser', android)
        self.assertIn('extensions/extension_install_ui_default.cc', android)
        self.assertNotIn('//apps/ui/views', android)
        self.assertNotIn('views/extensions/extension_popup.cc', android)
        desktop = audit.reachable_strings(text, dict(audit.ANDROID, is_android=False, toolkit_views=True))
        self.assertIn('//apps/ui/views', desktop)
        self.assertIn('views/extensions/extension_popup.cc', desktop)

    def test_missing_target_repairs_preserve_android_resources(self):
        resources = audit.reachable_strings((ROOT / 'chromium-overlay/chrome/browser/resources/BUILD.gn').read_text())
        self.assertIn('component_extension_resources', resources)
        self.assertNotIn('webid_resources', resources)
        for path in ['chrome/browser/ui/web_applications/BUILD.gn', 'chrome/browser/web_applications/BUILD.gn']:
            text = (ROOT / 'chromium-overlay' / path).read_text()
            self.assertNotIn('//chrome/test:test_support_ui', audit.reachable_strings(text))
            self.assertIn('//chrome/test:test_support_ui', audit.reachable_strings(text, dict(audit.ANDROID, is_android=False)))
        root = audit.reachable_strings((ROOT / 'chromium-overlay/BUILD.gn').read_text())
        self.assertNotIn('//extensions:extensions_unittests', root)
        ext = audit.reachable_strings((ROOT / 'chromium-overlay/extensions/BUILD.gn').read_text())
        self.assertNotIn('//content/browser/devtools:devtools_resources', ext)
        self.assertNotIn('$root_gen_dir/content/browser/devtools/devtools_resources.pak', ext)

    def test_extension_core_does_not_include_chrome_embedder(self):
        text = (ROOT / 'chromium-overlay/extensions/browser/extension_registrar.cc').read_text()
        self.assertNotRegex(text, r'#include "chrome/browser/(android|ui|profiles)/')
        self.assertNotIn('AppMenuBridge', text)
        self.assertNotIn('TabModelList', text)

    def test_android_declares_extension_and_web_app_include_owners(self):
        browser = audit.reachable_strings((ROOT / 'chromium-overlay/chrome/browser/BUILD.gn').read_text())
        for label in ['//extensions/browser', '//chrome/browser/web_applications',
                      '//chrome/browser/web_applications/app_service', '//components/keep_alive_registry',
                      '//chrome/browser/ui/tabs:tab_enums']:
            self.assertIn(label, browser)
        ui = audit.reachable_strings((ROOT / 'chromium-overlay/chrome/browser/ui/BUILD.gn').read_text())
        for label in ['//chrome/browser/web_applications', '//chrome/browser/web_applications/extensions',
                      '//components/services/app_service/public/cpp:intents', '//components/keep_alive_registry']:
            self.assertIn(label, ui)
        self.assertNotIn('//extensions/components/native_app_window', ui)
        sync = audit.reachable_strings((ROOT / 'chromium-overlay/components/background_sync/BUILD.gn').read_text())
        self.assertIn('//components/keep_alive_registry', sync)

    def test_android_test_support_exports_extension_test_owners(self):
        tests = audit.reachable_strings((ROOT / 'chromium-overlay/chrome/test/BUILD.gn').read_text())
        for label in ['//components/crx_file', '//extensions/common:test_support',
                      '//chrome/browser/extensions:test_support', '//components/ukm:test_support',
                      '//chrome/browser/supervised_user:test_support',
                      '//chrome/browser/resources:component_extension_resources_grit']:
            self.assertIn(label, tests)
        self.assertNotIn('//chrome/browser/resources:component_extension_resources', tests)
        weblayer = audit.reachable_strings((ROOT / 'chromium-overlay/weblayer/test/BUILD.gn').read_text())
        self.assertIn('//components/keep_alive_registry', weblayer)

    def test_android_keeps_storage_monitor_with_extensions(self):
        text = (ROOT / 'chromium-overlay/chrome/browser/BUILD.gn').read_text()
        self.assertRegex(text, r'if \(!enable_extensions\) \{\s*deps -= \[ "//components/storage_monitor" \]')

    def test_known_blockers_are_closed(self):
        self.assertEqual(audit.check(), [])


if __name__ == '__main__':
    unittest.main()

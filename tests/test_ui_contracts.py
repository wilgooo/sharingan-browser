from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1] / 'chromium-overlay'
TOP = 'chrome/browser/ui/android/toolbar/java/src/org/chromium/chrome/browser/toolbar/top/'
class UiContractsTest(unittest.TestCase):
    def test_swipe_overlay_api_and_render_properties(self):
        coordinator = (ROOT / (TOP + 'TopToolbarOverlayCoordinator.java')).read_text()
        mediator = (ROOT / (TOP + 'TopToolbarOverlayMediator.java')).read_text()
        layer = (ROOT / (TOP + 'TopToolbarSceneLayer.java')).read_text()
        for method in ['setManualVisibility', 'setAnonymize', 'setXOffset']:
            self.assertIn(method, coordinator)
            self.assertIn(method, mediator)
        for prop in ['X_OFFSET', 'ANONYMIZE']:
            self.assertIn(prop, layer)
        self.assertIn('int layoutsToShowOn', coordinator)
    def test_extension_menu_dispatch_contract(self):
        delegate = (ROOT / 'chrome/browser/ui/android/appmenu/java/src/org/chromium/chrome/browser/ui/appmenu/AppMenuDelegate.java').read_text()
        activity = (ROOT / 'chrome/android/java/src/org/chromium/chrome/browser/app/ChromeActivity.java').read_text()
        self.assertIn('setLastItemTitle(String itemTitle)', delegate)
        self.assertIn('mMenuTitleCondensed.startsWith("Extension: ")', activity)
        self.assertIn('chrome://extensions', activity)
    def test_tab_list_default_excludes_extension_schemes(self):
        source = (ROOT / 'chrome/browser/tabmodel/android/java/src/org/chromium/chrome/browser/tabmodel/TabList.java').read_text()
        self.assertIn('default int getLastNonExtensionActiveIndex()', source)
        for text in ['chrome-extension://', 'kiwi-extension://', 'getTimestampMillis()', 'INVALID_TAB_INDEX']:
            self.assertIn(text, source)
    def test_tab_switcher_uses_baseline_scene_signature(self):
        source = (ROOT / 'chrome/android/features/tab_ui/java/src/org/chromium/chrome/browser/tasks/tab_management/TabSwitcherLayout.java').read_text()
        self.assertNotIn('TitleCache', source)
        self.assertNotIn('layerTitleCache', source)

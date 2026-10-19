# Audit repair — 18 October 2026

Changes are local and unbuilt. No GitHub Actions dispatch, GN generation, native/Java compilation, push, or runtime test was performed. Monitoring remains paused.

## Confirmed blockers addressed

| Audit finding | Resolution |
| --- | --- |
| Native WebUI pulls desktop Mojo targets on Android | Restore `!is_android && !is_ios` guard in `ui/webui/BUILD.gn`. |
| 17 desktop resource targets and their PAKs pulled into Android | Restore platform guards in `chrome_paks.gni` around both `sources` and `deps`; preserve extension UI and component-extension resources in explicit Android/extension blocks. |
| Polymer enabled through unconditional bypasses | Use one shared `include_polymer` definition: desktop or Android with extensions, excluding iOS; remove all `|| true`/`if (true)` GN bypasses in the overlay. |
| Desktop content implementations compiled on Android | Restore desktop guard for DevTools resource extern and WebAuthn DevTools/Direct Sockets/Serial implementation group. Android binders already exclude Serial/Direct Sockets. |
| 25 missing source entries | Six files implemented, 19 stale entries removed; consumers of the removed DevTools helper removed too. Details in `config/audit-blockers.json`. |

## Source decisions and behavior

- **AppMenuBridge.java** and a new **sharingan_app_menu_bridge.cc** implement the extension action menu, rather than returning placeholder success. Native code enumerates enabled, visible actions, filters incognito access, rechecks extension/profile state at click time, and calls `ExtensionActionRunner::RunAction` for permission/event handling. Popups open as browser tabs. Java list, generated JNI list, and native GN list are wired. Menu labels escape control characters and click IDs are validated.
- **HandButton.java** uses the existing ChromeImageButton widget. Existing ToolbarPhone owns click/overscroll, tint and drawing behavior.
- **NightModeSettings.java** binds the existing night-mode XML and preference widget.
- **ToolbarSettings.java** now only supplies the restart notice used by the two existing preference widgets. The broken standalone toolbar-settings fragment entry is removed; the existing adaptive-toolbar settings remains.
- **global_shortcut_listener_android.cc/.h** explicitly reject system-wide shortcut registration on Android. This is unsupported functionality, not a stub that pretends success. Shared shortcut logic is restored and Android implementation is only compiled for Android.
- Eight AdCard/FeedCard source entries and ten unused old stack/accessibility/referrer source entries are removed. No Java/XML consumers were found in the overlay. `FixDevToolsWindow` and its call are removed.
- Inherited proxy-disable and embedded-DevTools menu actions depended on a missing Kiwi bridge with no native implementation. They are hidden and their call sites removed. This does not disable Sharingan developer mode or ZIP installation.
- The Linux removable-storage implementation is now selected explicitly for Linux/Android, rather than `|| true`. Its upstream `USE_UDEV` guard controls enumeration; this does not promise Android raw-storage access.

## Verification performed

- Overlay hash/source/XML/ZIP packaging verifier: **PASS**, 8,303 files.
- Host unit tests: **29 PASS**, including regression tests that reintroduce the former platform bypass and verify that both forbidden PAK and dependency become reachable.
- Audit gate: **PASS**, all 25 original source findings resolved, all 17 resource/dependency conflicts excluded for the Android environment, four desktop WebUI Mojo edges excluded, no unconditional GN platform bypass remains.
- New native checked-in include paths resolve against the pinned Chromium tree plus overlay; generated JNI header paths checked through the Java/JNI wiring gate.
- Cumulative `patches/sharingan.patch` regenerated against pinned Kiwi HEAD; reverse-apply check: **PASS**.
- Source/config/documentation `git diff --check` (excluding the generated patch): **PASS**. The cumulative patch contains blank context lines required by unified-diff syntax; its integrity is checked by reverse application instead.

`check_audit.py` is a conservative boolean-platform scope check, not a GN interpreter. Unknown conditions remain reachable. It is called by `verify_source.py` so future local/CI packaging checks cannot silently accept these known regressions. It does not evaluate templates, complete transitive dependencies, all generated sources, or C++/Java/TypeScript semantics.

## Remaining validation boundary

All confirmed missing-source and platform-edge blockers from the static audit are addressed in source. This is **not** a claim that the APK builds or that every remaining port issue has been discovered. GN, compiler/linker, WebUI asset loading, extension action/activeTab/popup behavior, import lifecycle and permissions require execution after the user authorizes it. The old guest_view/apps/keep_alive/HID port assertions remain scoped to Android extensions; their runtime platform support is still unverified.

Chromium 105 remains an obsolete prototype engine without Family Link. ZIP expanded-size quotas, reinstall identity/cleanup, modern engine maintenance and other audit risks are not represented as solved by these build-blocker changes. No retry should be started automatically.

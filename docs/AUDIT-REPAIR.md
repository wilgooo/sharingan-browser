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

## Build 14 follow-up (19 October 2026)

GN exposed `components/web_modal` through `extensions/browser:browser_sources`.
Pinned `app_window.cc` and `native_app_window.h` require its modal-manager/host
interfaces, so the dependency is retained. Inspection of the core shows generic
WebContents/input/visibility management and abstract native host interfaces, with
no Views/GTK dependency. The core is enabled only for Android with extensions;
desktop test targets remain excluded. This permits GN evaluation and does not
claim that Android app-window dialog presentation is implemented or tested.

## Build 15 follow-up (19 October 2026)

GN reached desktop Read Anything Mojo through a tautological Android renderer
guard. Separate Read Anything sources and bindings behind `!is_android`; keep
SearchBox and crx_file because Kiwi's Android renderer client instantiates and
queries SearchBox. A regression test exercises the former tautology.

## Build 16 follow-up (19 October 2026)

Media Router discovery was an unconditional extension dependency although its
mDNS consumer was already guarded by enable_service_discovery. Pinned feature
defaults disable service discovery on Android. Move the dependency into the
same feature block, preserving desktop consumers and the upstream assertion.
Regression coverage checks that both source and dependency follow the flag.

## Build 17 follow-up (19 October 2026)

A second unconditional discovery edge in platform_apps loaded the same desktop
target. Inspected all C++/header sources listed in the pinned target, including
Mac additions; none directly references discovery/DnsSd. Keep the legacy desktop
dependency under !is_android; Android does not load it. Add that second edge to
the regression gate. This does not claim the whole platform-app port compiles.

## Build 18: desktop Views in extension UI

Run 39265508909 failed GN at ui/views: assert(toolkit_views), reached via apps/ui/views. chrome/browser/ui's enable_extensions block mixed shared extension sources with Views dialogs and widgets. The pinned apps/ui/views target contains app_window_frame_view and requires ui/views; the JavaScript modal factory directly includes Views widget/constrained-window headers. Guard the Views source list and non-Mac apps/ui/views edge with toolkit_views. Shared extension sources/dependencies remain enabled. The host audit now models toolkit_views=false on Android and checks both desktop preservation and Android exclusion. This closes this observed graph edge, not proof that GN or Android runtime passes.

## Build 19: unresolved target graph

Run 39270602592 passed the previous Views assertion but GN reported unresolved labels. Removed unused Ads/Firebase Java dependencies from widget/android after finding no matching SDK consumers in overlay Java (the obsolete ad cards were removed in the earlier audit). Enabled component_extension_resources GRIT for Android extensions while retaining desktop guards on unrelated resources. Kept desktop extension test executables out of Android gn_all. Guarded desktop web-app browser/UI test target definitions, including their groups, with !is_android; the chrome/test consumers of these browser/UI targets are also unreachable for Android. Native extension GRIT resources moved from chrome unit_tests deps to data_deps so Android APK classpath generation does not expect a Java build_config from a native group. Shell test PAK excludes both the DevTools frontend PAK and dependency on Android, matching the pinned target definition (the frontend is desktop-only). No assertions removed. Android desktop test coverage is not claimed.

APT cache save succeeded despite GN failure: key apt-v1-ubuntu22-x64-2026-43-768b6e6d7c433d55d49a21f83e78f5b682c408c3817119fdee44ba6763fd73ad, GitHub cache ID 9167936439, 145343926 bytes. Overlay application finished within the same minute rather than the prior ~9-minute stage. GN/compile/runtime success remains unverified.

## Build 20: include validation

Run 39275093147 resolved every label and failed in `gn check` include validation (823 reports, 483 unique; see `outputs/Sharingan-build20-include-audit.json` from the audit pass). Kiwi compiles extension and web-app sources on Android, so their header owners (`//extensions/browser`, `//chrome/browser/web_applications`, `app_service`, `keep_alive_registry`, app-service public C++ and theme/colour headers) are in the Android graph, but the declaring `deps`/`allow_circular_includes_from` entries sat in desktop-only branches. Mirrored them under `is_android && enable_extensions` in `chrome/browser` and `chrome/browser/ui`, matching the desktop declarations rather than adding new edges. `//extensions/browser` brings kiosk, runtime, audio, mime_handler_private and the keyed-service factories through upstream public deps. `background_sync` and `chrome/browser/extensions` declare keep-alive and component-extension-resource owners on Android; StorageMonitor stays linked with extensions because BrowserProcessImpl destroys it.

`extensions/browser/extension_registrar.cc` no longer includes Chrome TabAndroid/TabModel/Profile or calls `AppMenuBridge_GetRunningExtensionsInternal`. That symbol had no definition in the overlay (a latent link error) and the Sharingan menu already rebuilds its extension entries on every `prepareMenu` through `AppMenuBridge.getRunningExtensions`, so the push refresh was redundant. The file now differs from Chromium 105 only by Kiwi's reload-on-terminate logic. `native_app_window` (Views) moved behind `toolkit_views`. Test targets get the same treatment: on Android, `//chrome/test:test_support` now public-deps the extension/web-app test owners that desktop exports (crx_file, extension test_support, ukm test_support, keep-alive, storage monitor), which also covers `unit_tests`, `policy:browser_tests`, `android_browsertests` and `web_applications_unit_tests`; `unit_tests` adds tab_enums, supervised-user and web-app test support and the component-extension-resources source_set, and `weblayer_browsertests` adds keep-alive. `gn check` stays enabled. GN/compile success is unverified until run 21.

## Build 21: snapcraft download in dependency install

Run 39281973774 (commit 1908e33) failed before GN in `06-system-dependencies`: Chromium 105's `install-build-deps.sh` adds `snapcraft` when apt lists it, and on Jammy that package's pre-install script downloads the `core24` snap from api.snapcraft.io, which timed out, so dpkg exited 100. The same stage passed in run 20, so this was a network failure, but snapcraft is unused by the Android build. The runner now executes staged copies of the two installer scripts with only that block removed (it fails if the upstream block changes); the Chromium checkout stays unmodified. The Build 20 GN repair remains untested on CI.

Run 39285822290 (gn-only, commit 795fec5) then failed the same stage with exit 126: the staged `install-build-deps.sh` was written without its executable bit, and the Android wrapper executes it directly. The staged copy now keeps the source file mode (100755 upstream). That run also skipped the package-cache restore because the cache steps were still limited to build mode; fixed in 2551c22.

## Build 23: native GRIT mistaken for Java resources

Run 39288202012 passed the staged installer but failed GN target resolution.
The Android test template filters deps by java_target_patterns; the native
component_extension_resources name matches the Android resource naming pattern,
so the APK requests a nonexistent Java build_config and the native library loses
its header dependency. Use component_extension_resources_grit directly, matching
the desktop unit test dependency and owning the generated header. Keep GN --check.
The regression gate now rejects the misleading resource target in Android test
deps. APT cache hit and successful restore are confirmed in this run's log.
Host checks do not establish GN or compilation success.

## Build 24: shortcut module generated input

Run 39549165827 passed the prior native-resource target error, then reported
three generated-input errors for keyboard_shortcut_list.js across toolchains.
Pinned Chromium's js/cr/ui preprocessing produces keyboard_shortcut_list.m.js;
the non-module input is not preprocessed on Android. Restore the module name
in generate_definitions and both find-shortcut imports so runtime/TypeScript
consumers agree with the producer. GN --check remains enabled.

## Build 26: Android resource inputs

GN --check succeeded; Ninja stopped before compilation on missing
values-xxhdpi/dimens.xml. Auditing the complete chrome_java_resources list
against the pinned Chromium tree and overlay also found 90 missing Kiwi
settings PNGs (18 names across five densities) and unused toolbar_preferences.xml.
Remove stale XML entries; density-independent dimens remain. Preserve settings
resource names with platform drawable aliases instead of absent bitmap assets.
Icons may look different and require device review. Add a resource-list existence
regression using a pinned Chromium path inventory. This does not prove AAPT,
compilation, or Android runtime passes.

## Build 27: complete literal Android resource audit

GN passed again. Ninja found gnt_rounded_corners_shape.xml before compiling.
Compared literal /res/ file inputs in every overlay .gn/.gni against the entire
pinned Chromium tree plus overlay, not only chrome/android. Found seven missing
widget entries: two GNT shapes and five feed/ad card layouts. All seven occur
only in the build list in the overlay; removed with the already removed legacy
ad-card code. Add this complete literal resource-input check and parsing of every
overlay res XML to verify_source.py, with missing-input/XML regression tests.
Variable/generated paths, transitive resource identifiers, GRIT/WebUI assets and
AAPT/link/compile semantics still require build validation; zero static missing
inputs is not a guarantee of a successful APK.

## Build 28: undeclared base-module icons

GN passed and C++ compilation began (including installer constants and Android
linker). Ninja reached 4230/68689 before prepare_resources rejected ten present
ic_foreground/ic_background PNGs in res_chromium_base not listed in its target.
Declare all ten across five densities and add reverse inventory coverage for
all overlay PNG/XML files in that target. Keep prepare_resources validation.

## Build 29: Android Polymer focus module

C++ compilation progressed to 15120/68689 Ninja steps; resource icon packaging
passed. TypeScript cr_action_menu imports focus_without_ink.m.js, but Chromium
preprocessing and declaration generation excluded Android. Move only that shared
module to unconditional preprocessing and definition inputs; retain desktop guards
for other modules. The modulize target already produces it. GN/TS checks remain
enabled. Host regression checks both producer and declaration reachability.

## Build 30: desktop inline-login GRIT input

The prior TypeScript failure passed. GRIT failed trying to package generated
inline_login_app.js on Android. Its components producer is only a resource dep
on desktop platforms; inline_login_ui is gated by DICE/ChromeOS/Fuchsia. Restore
not-is-Android on the guest-page/inline-login GRIT block instead of the inherited
tautology. Shared extension resource blocks remain enabled. Add guard regression.

## Build 31 / retry 32: desktop WebUI resource audit

GRIT passed inline login then failed on generated Media Router internals JS.
Audited file-bearing non-string overlay GRD/GRDP entries and recorded guards
and generated/static paths in config/webui-resource-audit.json. In the browser
manifest six inherited tautologies exposed desktop-only groups: Media Router,
Desktop Sharing Hub, Chrome Cart, tab-ranker models, desktop NTP and About System.
Restore all six to not is_android. Browser resources GN puts Media Router build_ts
and sharing protobuf generation behind !is_android. Android reachability checks
exclude Media Router UI, NTP resource cache and Cart service consumers. Other
generated groups retain feature/platform guards matching their GN producers
(certificate viewer, NaCl, conflicts, reset-password, ChromeOS and Android
explore-sites); shared USB/Mojo and content/dev-ui resources remain enabled.
String-only GRDP platform widenings remain because Android extension UI can use
those strings; this audit does not remove extension assets or disable GN/GRIT.
Regression tests cover all six groups and representative absent consumers.
Inventory is a review aid, not proof of all generated output names, recursive
imports or runtime behavior. Build 32 must still validate GRIT and compilation.

## Build 32: undeclared app resources

prepare_resources rejected present locale XMLs absent from chrome_java_resources.
Reverse inventory of the entire app res overlay found 35 undeclared files: 33
translations and two preference XMLs. Declare all and add full app-resource
reverse inventory regression, complementing missing-input and base-icon checks.
Keep strict resource discovery. AAPT/runtime correctness remains unverified.

## Build 33: preference API mismatch

GN and chrome_app_java_resources passed (26992/68689). Compilation stopped at
34069 on absent writeStringUnchecked. Audit of all overlay Java singleton and
typed-variable SharedPreferencesManager calls found five incompatible calls:
two String, two Int, one Boolean writes across WebContentsDarkModeController,
ChromeApplicationImpl and ChromeActivity. Use ContextUtils app preferences Editor
putString/putInt/putBoolean with apply, preserving keys, types and async storage
used by existing readers. These are legacy Kiwi keys, outside Chromium's key
registry; do not disable the registry checker or add unchecked manager methods.
Pinned public-method inventory and regression scan cover all detected manager
receivers. This is a method-name audit of this API, not a Java typechecker or
a guarantee about unrelated APIs, overloads, inherited or inferred receivers.
Full Java/C++ compilation remains the authoritative compatibility check.

## Build 34: missing UrlBarData helper

Four replaceOnce calls in AutocompleteMediator and LocationBarMediator refer to
an absent helper. All are under matching startsWith checks; replace only that
prefix using String.substring, preserving the remainder including repeated
scheme text. No GN or compiler checks disabled.

## Build 35: omitted toolbar swipe Java source

ToolbarSwipeSceneLayer exists in pinned Chromium and is already in JNI inputs,
but absent from chrome_java_sources.gni while ToolbarSwipeLayout imports it.
Restore its Java compilation entry alongside other scene layers.

## Build 36: coordinated Java UI contracts

31 diagnostics span toolbar overlay, tab switcher, activity resources/imports,
extension menu delegate and TabList implementations. Restore pinned baseline
TopToolbarOverlayCoordinator/Mediator/Properties/SceneLayer plus mediator tests;
update the top toolbar caller to layout mask/manual visibility arguments. Native
scene implementation is inherited baseline, so Java JNI parameters now agree.
Adapt TabSwitcherLayout to baseline scene methods without LayerTitleCache.
Keep extension menu dispatch through a default AppMenuDelegate title callback,
with ChromeActivity's existing override handling Extension IDs. TabList default
selects current non-extension tab or most recently active non-extension tab;
empty/all-extension lists return INVALID_TAB_INDEX. Existing overrides remain.
Restore ContextUtils import, use platform color lookup, declare missing menu IDs
and resizing color. Main layout falls back to baseline top toolbar because the
old bottom-toolbar layout is absent; no extension loading/action code removed.
This is host/static validation, not full Android compilation or device testing.

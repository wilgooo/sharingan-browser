# Audited Kiwi–Chromium baseline (2026-10-18)

This replaces the incompatible Revived/Chromium 132 combination used in run #4.
It is a source-aligned experimental baseline, not yet a verified APK build.
Chromium 105 is obsolete: use any resulting APK for isolated development tests,
not everyday browsing or sensitive accounts. Modern engine maintenance is a separate substantial port.

## Pinned source

- Official Kiwi: `kiwibrowser/src.next`, branch `kiwi`, commit `7be7edd1532148f22103cb4c5a1964d96297836f`.
- Chromium tag `105.0.5195.24`, commit `64038a114b86434efcce9c36697be10e333f911a`.
- Both official Kiwi `CHROMIUM_VERSION` and bundled `chrome/VERSION` specify 105.0.5195.24. `KIWI_VERSION` is the application version 105.0.5195.33; it is not used to select the engine.
- Depot tools pinned in `config/upstream.lock.json`; GN, Clang, Android SDK/NDK/JDK and dependency revisions come from Chromium 105 DEPS. Depot tools remain the revision tested during earlier dependency sync; compatibility with this older DEPS still needs CI.

## Evidence beyond version strings

Compared Git blob object IDs from `git ls-tree -r` of the two pinned commits, for all source directories included in the overlay:

| Official Kiwi overlay | Count |
| --- | ---: |
| Byte-identical to Chromium 105.0.5195.24 | 7,746 |
| Existing Chromium files modified by Kiwi | 364 |
| Kiwi-only files | 176 |
| Total before Sharingan additions | 8,286 |

Of 99 GN files in the official overlay, 84 match Chromium 105 exactly and 15 contain Kiwi changes. In particular, `base/BUILD.gn`, `chrome/android/BUILD.gn`, and `chrome/browser/buildflags.gni` match the pinned Chromium baseline. The two missing imports from the previous run, `build/config/chromecast_build.gni` and `build/rust/mixed_component.gni`, exist in Chromium 105. Its root BUILD.gn does not reference the incompatible `enable_updater` flag.

Static literal-import inspection of the 99 GN files resolves all imports in the Chromium/overlay tree except four paths supplied by separate DEPS checkouts (Fuchsia SDK, ICU, WebRTC, V8). This is not equivalent to GN evaluation or compilation.

The official `chromium` branch currently points at 132, but the `kiwi` branch was not rebased to that snapshot. The official build workflow delegates to an external build service/cache; its success is not proof of an independent source build. We do not rely on that service or its prebuilt APKs.

## Sharingan port and CI changes

Applied and regenerated `patches/sharingan.patch` against the official Kiwi commit, preserving launcher branding, `com.sharingan.browser`, developer mode, SAF ZIP picker, native install callbacks, and the root-manifest installer fix. The final overlay contains 8,289 files. Changes unique to the unrelated Revived fork are no longer mixed into this baseline.

- Standard free `ubuntu-22.04` x86-64 runner: supplies legacy ncurses5/i386 libraries used by the old Android tools.
- Use Chromium 105 `build/install-build-deps-android.sh --unsupported`: the flag acknowledges Jammy is newer than this script's distro allowlist; it does not bypass package failures.
- Install system Ninja because Chromium 105 does not provision `third_party/ninja/ninja`.
- Remove the newer `use_siso` GN argument, disable NaCl/PDF/plugins as in Kiwi's reference build, keep two workers, no ThinLTO/PGO, and one linker.
- The preparation script verifies both tag and audited Chromium commit; package checks reject a mismatch between engine version and overlay `chrome/VERSION`.
- No paid runner, remote build service, billing changes, or repacking another APK.

## Verification so far

23 host tooling tests pass. All 8,289 file hashes, JNI/GN references, Android XML/resources and MV3 fixture packaging pass. Workflow actionlint and shell syntax checks pass. The regenerated patch passes reverse application checking against the ported source. `prepare.py` also applied the overlay to a real pinned Chromium 105 sparse checkout and verified an identical second application; this checks preparation, not a complete build tree. Whitespace checking of first-party changes passes; the source snapshot retains upstream whitespace and the patch retains required diff context whitespace.

Linux dependency sync, GN generation, Java/C++ compilation, actual APK signing/package identity and Android runtime remain unverified for this baseline until CI/device results are recorded.

## Sources

- [Official Kiwi pinned source](https://github.com/kiwibrowser/src.next/tree/7be7edd1532148f22103cb4c5a1964d96297836f)
- [Chromium pinned source](https://chromium.googlesource.com/chromium/src/+/64038a114b86434efcce9c36697be10e333f911a/)
- [Kiwi build reference](https://github.com/kiwibrowser/src.next/blob/7be7edd1532148f22103cb4c5a1964d96297836f/.build/production_build_reference/args.gn)

## Static blocker repair (2026-10-18, not built)

The follow-up repair removes the audited desktop resource/Mojo edges from Android,
resolves all 25 identified missing source entries, and adds a host-only regression
gate. The current overlay has 8,303 files. See [AUDIT-REPAIR.md](AUDIT-REPAIR.md)
for behavior changes and validation limits. `build_verified` remains false.

# Build blocked by baseline incompatibility

> Historical report for run #4. On 2026-10-18 the incompatible fork/132 combination was replaced by official Kiwi/Chromium 105. See [BASELINE.md](BASELINE.md). A successful APK is still unverified.

Observed on 14 October 2026 in [run #4](https://github.com/wilgooo/sharingan-browser/actions/runs/38583341931), source commit `934c46a87657be205d93b744f2c9dfdd5bcc4402`. Total workflow duration: 53m22s. No APK was produced and native compilation never started.

## What passed

Source verification and all 22 host tooling tests passed. The runner fetched depot_tools and Chromium, synchronized dependencies, installed system packages, ran hooks, and applied all 8,291 overlay files. Earlier HTTP 503 retry handling and the direct Chromium-pinned GN invocation allowed the build to reach GN source evaluation.

## Evidence

GN stopped at upstream `//BUILD.gn:174`:

```text
ERROR at //BUILD.gn:174:24: Undefined identifier
    if (!is_fuchsia && enable_updater) {
                       ^-------------
```

The root build file imports `//chrome/browser/buildflags.gni`. The bundled overlay replaces that file with an older definition containing only `enable_chromium_updater`; Chromium 132's file defines `enable_updater`, `enable_platform_experience`, and `enable_update_notifications` instead.

Further inspection found independent incompatibilities in the bundled `base/BUILD.gn`:

| Imported path | Chromium 132.0.6834.83 lookup |
|---|---|
| `build/config/chromecast_build.gni` | Absent (Gitiles HTTP 404) |
| `build/rust/mixed_component.gni` | Absent (Gitiles HTTP 404) |
| `base/trace_event/tracing.gni` | Present (HTTP 200; comparison check) |

Primary references: [Chromium 132 root BUILD.gn](https://chromium.googlesource.com/chromium/src/+/132.0.6834.83/BUILD.gn), [browser build flags](https://chromium.googlesource.com/chromium/src/+/132.0.6834.83/chrome/browser/buildflags.gni), [build/config tree](https://chromium.googlesource.com/chromium/src/+/132.0.6834.83/build/config/), [build/rust tree](https://chromium.googlesource.com/chromium/src/+/132.0.6834.83/build/rust/).

Version metadata is inconsistent: upstream root `VERSION` says 93.0.4577.21, bundled `chrome/VERSION` says 105.0.5195.24, while the fork's version metadata nominated 132.0.6834.83. These values do not establish a compatible build baseline. The overlay contains 99 GN build/configuration files, so restoring one variable does not establish that the remaining build graph or C++/Java APIs are compatible.

## Next engineering step

Establish the exact upstream Chromium revision expected by the fork, or select a source-buildable Android extension fork and port Sharingan's branding/developer-mode/ZIP changes onto it. Reconcile GN targets and source APIs, then validate GN generation before spending time on compilation. Merely downgrading the checkout to the version string in one file is not a verified repair.

Automatic retries are paused at this source compatibility blocker. The last observed failure was not a disk, RAM, or job-timeout failure; this also does not establish that a complete Chromium compile will fit the standard runner. The manual workflow remains available for a repaired baseline. No binaries from another browser were substituted or repackaged as a successful Sharingan build.

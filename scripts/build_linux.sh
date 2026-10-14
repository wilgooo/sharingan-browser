#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Build requires Linux x86-64. Source checks can run on macOS.' >&2
  exit 1
fi
[[ $# == 1 ]] || { echo 'Usage: bash scripts/build_linux.sh /path/to/chromium/src' >&2; exit 2; }
SOURCE_ROOT=$(cd "$1" && pwd)
[[ -f "$SOURCE_ROOT/.sharingan-source.json" ]] || { echo 'Run prepare.py first.' >&2; exit 2; }
[[ -x "$SOURCE_ROOT/buildtools/linux64/gn" ]] || { echo 'Chromium GN binary missing; sync dependencies first.' >&2; exit 2; }
command -v autoninja >/dev/null
cd "$SOURCE_ROOT"
# Fail at GN generation if the inherited overlay is incompatible. Never fall back
# to downloading/repacking an existing APK.
buildtools/linux64/gn gen out/sharingan_arm64 --check --fail-on-unused-args
autoninja -C out/sharingan_arm64 chrome_public_apk
[[ -f out/sharingan_arm64/apks/ChromePublic.apk ]]
cp out/sharingan_arm64/apks/ChromePublic.apk out/sharingan_arm64/apks/SharinganBrowser-dev-arm64.apk
printf '%s\n' "$SOURCE_ROOT/out/sharingan_arm64/apks/SharinganBrowser-dev-arm64.apk"

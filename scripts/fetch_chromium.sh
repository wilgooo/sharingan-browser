#!/usr/bin/env bash
# Fetch only. Does not install OS packages, run hooks, or build an APK.
set -euo pipefail
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Chromium Android requires a Linux x86-64 builder.' >&2
  exit 1
fi
if [[ $# != 1 ]]; then
  echo 'Usage: bash scripts/fetch_chromium.sh /absolute/path/to/new-build-workspace' >&2
  exit 2
fi
BUILD_ROOT="$1"
[[ "$BUILD_ROOT" = /* && "$BUILD_ROOT" != *' '* ]] || { echo 'Use an absolute path without spaces.' >&2; exit 2; }
[[ ! -e "$BUILD_ROOT" ]] || { echo 'Choose a new directory; refusing to overwrite an existing checkout.' >&2; exit 2; }
mkdir -p "$BUILD_ROOT"
cd "$BUILD_ROOT"
AVAILABLE_KB=$(df -Pk . | awk 'NR==2 {print $4}')
[[ "$AVAILABLE_KB" -ge 104857600 ]] || { echo 'At least 100 GiB free space required; 200+ GiB recommended.' >&2; exit 1; }
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git depot_tools
export PATH="$BUILD_ROOT/depot_tools:$PATH"
git clone --depth 1 --branch 132.0.6834.83 https://chromium.googlesource.com/chromium/src.git src
cat > .gclient <<'GCLIENT'
solutions = [{
  'name': 'src',
  'url': 'https://chromium.googlesource.com/chromium/src.git',
  'managed': False,
  'custom_deps': {},
}]
target_os = ['android']
GCLIENT
gclient sync --nohooks --no-history
printf '%s\n' 'Source fetched. Follow docs/BUILD_LINUX.md to install dependencies and prepare the overlay.'

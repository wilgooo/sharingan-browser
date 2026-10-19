# Retry preparation cache

The standard Ubuntu 22.04 workflow restores/saves up to 1 GiB of complete APT
`.deb` downloads. Keys include OS/architecture, ISO week, the upstream lock and
cache-helper hash. GN-only/source-overlay fixes reuse the same key within the
week. An explicit save step runs even after GN or compilation fails, provided
system dependency installation produced a non-empty cache. Cache failures are
non-fatal; the build can download packages normally.

The first run with this workflow seeds the cache. A later matching run can reuse
it. APT still installs packages and checks repository metadata; this is not a
snapshot of installed `/usr` or dpkg state. Package version changes may still
require downloads. Only complete regular `.deb` files are exported before
`apt-get clean`; partial files and symlinks are excluded. Installed state, source
checkouts, credentials, generated GN output and APKs are not cached.

The full Chromium/DEPS checkout, Android toolchain and compiler output remain
uncached. Their size and invalidation need a separate measured cache strategy;
this change does not claim to remove all preparation time.

`prepare.py` also inventories tracked files with one `git ls-files -z` call,
instead of thousands of subprocesses for the overlay. Existing checksum,
revision, dirty-checkout, symlink and untracked-file protection remains intact.

Validation: host tests and source-package verifier. Cache hits and actual time
savings must be measured on subsequent CI runs; no speedup figure is promised.
The currently running workflow keeps its original configuration.

Reference: https://github.com/actions/cache/blob/main/README.md

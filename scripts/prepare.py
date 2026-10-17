#!/usr/bin/env python3
"""Apply the bundled source overlay to a clean, dedicated Chromium checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def git(src, *args):
    return subprocess.check_output(['git', '-C', str(src), *args], text=True).strip()

def prepare(src):
    src = src.resolve(strict=True)
    lock = json.loads((ROOT / 'config/upstream.lock.json').read_text())
    manifest_path = ROOT / 'config/overlay.sha256.json'
    manifest = json.loads(manifest_path.read_text())
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    stamp = src / '.sharingan-source.json'
    if stamp.exists():
        previous = json.loads(stamp.read_text())
        if previous.get('overlay_digest') != digest:
            raise RuntimeError('A different Sharingan overlay exists. Use a new checkout.')
        for name, expected in manifest.items():
            if hashlib.sha256((src / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError('Prepared source changed: ' + name + '. Preserve your edits; use a new checkout.')
        print('This overlay is already applied and its files match.')
        return
    candidate = lock['chromium_version_candidate']
    if git(src, 'rev-parse', 'HEAD') != git(src, 'rev-parse', 'refs/tags/' + candidate + '^{commit}'):
        raise RuntimeError('Expected Chromium tag ' + candidate + '; refusing a different revision.')
    if lock.get('chromium_commit') and git(src, 'rev-parse', 'HEAD') != lock['chromium_commit']:
        raise RuntimeError('Chromium commit differs from the audited baseline; refusing to apply overlay.')
    if git(src, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Tracked source files have local changes. Use a clean dedicated checkout.')
    out = src / 'out/sharingan_arm64'
    if (out / 'args.gn').exists():
        raise RuntimeError('Existing Sharingan build args found; use a clean dedicated checkout.')
    # Preflight every file before writing. Reject symlinks and traversal destinations.
    for name, expected in manifest.items():
        source = ROOT / 'chromium-overlay' / name
        dest = src / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError('Invalid overlay file: ' + name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Overlay checksum mismatch: ' + name)
        if not dest.resolve().is_relative_to(src):
            raise RuntimeError('Destination escapes checkout: ' + name)
        if dest.is_symlink():
            raise RuntimeError('Destination is a symlink: ' + name)
        if dest.exists() and not git(src, 'ls-files', '--', name):
            raise RuntimeError('Untracked file would be replaced: ' + name)
    for name in manifest:
        dest = src / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'chromium-overlay' / name, dest)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'config/args.gn', out / 'args.gn')
    stamp.write_text(json.dumps({'overlay_digest': digest, 'upstream': lock}, indent=2) + '\n')
    print(f'Applied {len(manifest)} source files to {src}.')
    print('EXPERIMENTAL: Chromium ' + candidate + '; compilation and Android runtime still require validation.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('chromium_src', type=Path)
    args = parser.parse_args()
    try:
        prepare(args.chromium_src)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))

"""Carry the ninja output directory between free-runner jobs.

A full compile does not fit in one six-hour job. Each job archives out/ and the
next one restores it. Every job checks Chromium out afresh, so all source
mtimes are pinned to a fixed past epoch; only overlay files whose content
changed since the archived outputs were produced are bumped to "now", so ninja
rebuilds exactly those and their dependents.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

# 2001-01-01T00:00:00Z: older than any archived output, valid inside zip/jar files.
SOURCE_EPOCH = 978307200
MARKER = '.sharingan-resume.json'
COMPRESSOR = 'zstd -T0 -3'
# Fingerprinted inputs that change every compile command; a mismatch discards the archive.
FINGERPRINT_FILES = ('config/upstream.lock.json', 'config/args.free.gn')


def fingerprint(root):
    return {name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
            for name in FINGERPRINT_FILES}


def changed_overlay_files(previous, current):
    """Names whose content differs, including files added or dropped from the overlay."""
    return sorted(name for name in set(previous) | set(current)
                  if previous.get(name) != current.get(name))


def consistent_overlay(previous, current, complete):
    """Overlay state the archived outputs are known to match.

    An interrupted or failed compile may not have rebuilt every dependent of a
    changed file, so those files keep their previous state and are bumped
    again by the next job.
    """
    if complete or previous is None:
        return dict(current)
    result = dict(current)
    for name in changed_overlay_files(previous, current):
        if name in previous:
            result[name] = previous[name]
        else:
            result.pop(name, None)
    return result


def pin_source_mtimes(src, epoch=SOURCE_EPOCH):
    """Set every checkout file except out/ and .git/ to the fixed epoch."""
    src = Path(src)
    skipped = {src / 'out', src / '.git'}
    count = 0
    for directory, subdirs, files in os.walk(src):
        here = Path(directory)
        subdirs[:] = [d for d in subdirs if here / d not in skipped]
        for name in files:
            os.utime(here / name, (epoch, epoch), follow_symlinks=False)
            count += 1
    return count


def bump(src, names, now=None):
    now = time.time() if now is None else now
    touched = []
    for name in names:
        path = Path(src) / name
        if path.is_file() and not path.is_symlink():
            os.utime(path, (now, now))
            touched.append(name)
    return touched


def stash(out, archive, root, overlay, previous_overlay, complete, compressor=COMPRESSOR):
    """Record which overlay the outputs match, then archive out/ with exact mtimes."""
    out, archive = Path(out), Path(archive)
    marker = {'fingerprint': fingerprint(root),
              'overlay': consistent_overlay(previous_overlay, overlay, complete)}
    (out / MARKER).write_text(json.dumps(marker, indent=2, sort_keys=True) + '\n')
    archive.parent.mkdir(parents=True, exist_ok=True)
    partial = archive.with_name(archive.name + '.partial')
    # pax keeps sub-second mtimes, which ninja compares against its build log.
    subprocess.run(['tar', '--format=pax', f'--use-compress-program={compressor}',
                    '-cf', str(partial), '-C', str(out), '.'], check=True)
    partial.replace(archive)
    return archive.stat().st_size


def restore(src, out, archive, root, overlay, compressor=COMPRESSOR):
    """Unpack a previous job's out/; return its overlay state, or None to build cleanly."""
    src, out, archive = Path(src), Path(out), Path(archive)
    if not archive.is_file():
        return None
    out.mkdir(parents=True, exist_ok=True)
    try:
        # bsdtar runs the program as given; GNU tar adds its own -d, which repeats harmlessly.
        decompressor = compressor.split()[0] + ' -d'
        subprocess.run(['tar', f'--use-compress-program={decompressor}',
                        '-xf', str(archive), '-C', str(out)], check=True)
        marker = json.loads((out / MARKER).read_text())
    except (OSError, ValueError, subprocess.CalledProcessError):
        marker = {}
    finally:
        # The archive is only needed until it is unpacked; free its space for compiling.
        archive.unlink()
    if marker.get('fingerprint') != fingerprint(root) or not isinstance(marker.get('overlay'), dict):
        # Unusable or foreign outputs: a clean build is slower but always correct.
        shutil.rmtree(out)
        out.mkdir(parents=True)
        return None
    previous = marker['overlay']
    pin_source_mtimes(src)
    bump(src, changed_overlay_files(previous, overlay))
    return previous

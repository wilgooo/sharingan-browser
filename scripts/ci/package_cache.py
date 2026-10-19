"""Bounded cache of APT download files, never installed system directories."""
from pathlib import Path
import shutil

MAX_BYTES = 1024 ** 3


def export_packages(archives, destination, limit=MAX_BYTES):
    """Keep the newest complete regular .deb files within a fixed byte budget."""
    archives, destination = Path(archives), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    # This directory is reserved for this helper; never follow restored symlinks.
    for path in destination.iterdir():
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            raise RuntimeError('Unexpected directory in package cache: ' + str(path))
    candidates = [p for p in archives.glob('*.deb') if p.is_file() and not p.is_symlink()]
    total = 0
    count = 0
    for path in sorted(candidates, key=lambda p: (-p.stat().st_mtime, p.name)):
        size = path.stat().st_size
        if size == 0 or total + size > limit:
            continue
        shutil.copy2(path, destination / path.name)
        total += size
        count += 1
    if count:
        (destination / '.ready').write_text(f'{count} packages, {total} bytes\n')
    return {'packages': count, 'bytes': total, 'limit_bytes': limit}

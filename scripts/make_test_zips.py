#!/usr/bin/env python3
"""Generate deterministic positive/negative fixtures. Never extract an archive."""
from pathlib import Path
import json
import zipfile
ROOT = Path(__file__).resolve().parents[1]

def write_zip(path, files):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)

def main():
    target = ROOT / 'examples/zips'
    target.mkdir(exist_ok=True)
    files = {p.name: p.read_bytes() for p in (ROOT / 'examples/hello-sharingan').iterdir() if p.is_file()}
    write_zip(target / 'hello-sharingan.zip', files)
    write_zip(target / 'missing-manifest.zip', {'content.js': b'// No manifest.'})
    write_zip(target / 'nested-manifest.zip', {'nested/' + k: v for k, v in files.items()})
    write_zip(target / 'invalid-manifest.zip', {'manifest.json': b'{not json'})
    write_zip(target / 'traversal.zip', {**files, '../sharingan-test-escape.txt': b'Harmless test marker; must never be extracted outside destination.'})
    invalid = dict(files)
    manifest = json.loads(invalid['manifest.json'])
    manifest['content_scripts'][0]['js'] = ['does-not-exist.js']
    invalid['manifest.json'] = json.dumps(manifest).encode()
    write_zip(target / 'missing-script.zip', invalid)
    (target / 'not-a-zip.zip').write_text('This is not a ZIP archive.\n')
    print('Created seven ZIP fixtures.')

if __name__ == '__main__':
    main()

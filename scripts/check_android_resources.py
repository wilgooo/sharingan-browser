"""Check literal Android resource inputs in every overlay GN/GNI file.
Generated/variable paths are left to GN and Ninja. Inventory is pinned Chromium.
"""
from pathlib import Path
import json
import posixpath
import re
import xml.etree.ElementTree as ET


def check(root):
    overlay = root / 'chromium-overlay'
    inherited = set(json.loads((root / 'config/chromium_android_resource_paths.json').read_text()))
    errors = []
    for path in overlay.rglob('*'):
        if path.suffix in ('.gn', '.gni'):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if line.lstrip().startswith('#'):
                    continue
                for value in re.findall(r'"([^"\n]+)"', line):
                    if '/res/' not in value or any(c in value for c in '$:*'):
                        continue
                    rel = posixpath.normpath(value[2:] if value.startswith('//') else
                                             str(path.parent.relative_to(overlay)) + '/' + value)
                    if '.' not in Path(rel).name:
                        continue
                    if not (overlay / rel).is_file() and rel not in inherited:
                        errors.append(f'{path.relative_to(overlay)}:{number}: missing {rel}')
        elif path.suffix == '.xml' and '/res/' in path.as_posix():
            try:
                ET.parse(path)
            except ET.ParseError as exc:
                errors.append(f'{path.relative_to(overlay)}: invalid XML: {exc}')
    return errors

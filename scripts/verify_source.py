#!/usr/bin/env python3
"""Host-only packaging checks. This does NOT compile Java, C++, GN, or an APK."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from check_audit import check as check_audit
from check_android_resources import check as check_android_resources

ROOT = Path(__file__).resolve().parents[1]

def main():
    overlay = ROOT / 'chromium-overlay'
    lock = json.loads((ROOT / 'config/upstream.lock.json').read_text())
    version = dict(line.split('=', 1) for line in
                   (overlay / 'chrome/VERSION').read_text().splitlines() if '=' in line)
    assert '.'.join(version[key] for key in ('MAJOR', 'MINOR', 'BUILD', 'PATCH')) == lock['chromium_version_candidate'], 'Overlay and Chromium versions disagree.'
    manifest = json.loads((ROOT / 'config/overlay.sha256.json').read_text())
    for name, digest in manifest.items():
        path = overlay / name
        assert path.is_file() and not path.is_symlink(), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    android = overlay / 'chrome/android'
    java_name = 'java/src/org/chromium/chrome/browser/extensions/DevModeExtensionLoader.java'
    assert java_name in (android / 'chrome_java_sources.gni').read_text()
    jni = (android / 'BUILD.gn').read_text().split('generate_jni("chrome_jni_headers")')[1]
    assert java_name in jni.split('\n}')[0]
    assert 'dev_mode_extension_loader.cc' in (overlay / 'chrome/browser/extensions/BUILD.gn').read_text()
    for name in ['java/res/values/strings.xml', 'java/res/menu/main_menu.xml',
                 'java/res/xml/main_preferences.xml', 'java/res/drawable/sharingan_launcher.xml']:
        ET.parse(android / name)
    resources = ET.parse(android / 'java/res/values/strings.xml').getroot()
    strings = {element.attrib['name'] for element in resources if 'name' in element.attrib}
    for name in ['java/res/menu/main_menu.xml', 'java/res/xml/main_preferences.xml', 'java/AndroidManifest.xml']:
        for resource in re.findall(r'@string/(sharingan_\w+)', (android / name).read_text()):
            assert resource in strings, resource
    java = (android / java_name).read_text()
    for resource in re.findall(r'R.string.(sharingan_\w+)', java):
        assert resource in strings, resource
    assert 'com.sharingan.browser' in (ROOT / 'config/args.gn').read_text()
    with zipfile.ZipFile(ROOT / 'examples/zips/hello-sharingan.zip') as archive:
        data = json.loads(archive.read('manifest.json'))
        assert data['manifest_version'] == 3
        assert data['background']['service_worker'] in archive.namelist()
        assert data['action']['default_popup'] in archive.namelist()
        for script in data['content_scripts'][0]['js']:
            assert script in archive.namelist()
    workflows = {p.relative_to(ROOT).as_posix() for p in (ROOT / '.github/workflows').glob('*')}
    assert workflows == {'.github/workflows/android-free.yml',
                         '.github/workflows/android-stage.yml'}, 'Unexpected inherited workflow.'
    audit_errors = check_audit(ROOT) + check_android_resources(ROOT)
    assert not audit_errors, '\n'.join(audit_errors)
    print(f'PASS: {len(manifest)} file hashes; JNI/GN source references; Android XML/resources; MV3 fixture packaging.')
    print('NOT TESTED: compilation, APK installation, extension execution, Web Store compatibility.')

if __name__ == '__main__':
    main()

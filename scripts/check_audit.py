#!/usr/bin/env python3
"""Host-only regression gate for the audited blockers; does not execute GN.

This deliberately handles boolean platform guards only. Unknown expressions are
conservative: their contents remain reachable. This is not a GN interpreter.
"""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ANDROID = dict(is_android=True, is_ios=False, is_win=False, is_mac=False,
               is_linux=False, is_fuchsia=False, is_chromeos=False,
               is_chromeos_ash=False, is_chromeos_lacros=False,
               toolkit_views=False, enable_extensions=True, include_polymer=True, enable_service_discovery=False)


def condition(expr, values):
    expr = re.sub(r'\btrue\b', 'True', expr)
    expr = re.sub(r'\bfalse\b', 'False', expr)
    expr = re.sub(r'!(?!=)', ' not ', expr).replace('&&', ' and ').replace('||', ' or ')
    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name):
            return values.get(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = visit(node.operand)
            return None if value is None else not value
        if isinstance(node, ast.BoolOp):
            parts = [visit(n) for n in node.values]
            if isinstance(node.op, ast.And):
                return False if False in parts else (None if None in parts else True)
            return True if True in parts else (None if None in parts else False)
        return None
    try:
        return visit(ast.parse(expr.strip(), mode='eval').body)
    except SyntaxError:
        return None


def reachable_strings(source, values=ANDROID):
    # Tokenize strings/comments first so braces in strings and comments are inert.
    token = re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|\bif\s*\(([^{}]*?)\)\s*\{|\belse\s*\{|[{}]', re.S)
    stack = []
    closed = None
    result = []
    for match in token.finditer(source):
        value = match.group()
        if value.startswith('#'):
            continue
        if value.startswith('if'):
            stack.append(condition(match.group(1), values))
        elif value.startswith('else'):
            stack.append(None if closed is None else not closed)
        elif value == '{':
            stack.append(None)
        elif value == '}':
            if not stack:
                raise ValueError('Unbalanced GN braces')
            closed = stack.pop()
        elif False not in stack:
            result.append(json.loads(value))
    if stack:
        raise ValueError('Unbalanced GN braces')
    return result


def check(root=ROOT):
    overlay = root / 'chromium-overlay'
    audit = json.loads((root / 'config/audit-blockers.json').read_text())
    errors = []
    for item in audit['missing_sources']:
        target = overlay / item['missing']
        gn = (overlay / item['file']).read_text()
        if item['resolution'] == 'implemented':
            if not target.is_file():
                errors.append('Missing implementation: ' + item['missing'])
            if target.name + '"' not in gn:
                errors.append('Implementation absent from sources: ' + target.name)
        elif target.name + '"' in gn:
            errors.append('Removed legacy source still referenced: ' + target.name)
    for filename, forbidden in audit['android_forbidden'].items():
        reachable = reachable_strings((overlay / filename).read_text())
        for label in forbidden:
            if label in reachable:
                errors.append('Android reaches desktop dependency/resource: ' + filename + ': ' + label)
    for filename in overlay.rglob('*'):
        if filename.suffix not in ('.gn', '.gni'):
            continue
        text = re.sub(r'#[^\n]*', '', filename.read_text())
        if re.search(r'\|\|\s*true\b|\bif\s*\(\s*true\s*\)', text):
            errors.append('Unconditional platform bypass: ' + str(filename.relative_to(overlay)))
    java = (overlay / 'chrome/android/chrome_java_sources.gni').read_text()
    jni = (overlay / 'chrome/android/BUILD.gn').read_text().split('generate_jni("chrome_jni_headers")')[1].split('\n}')[0]
    native = (overlay / 'chrome/browser/extensions/BUILD.gn').read_text()
    for name in ['AppMenuBridge', 'extensions/DevModeExtensionLoader']:
        path = 'java/src/org/chromium/chrome/browser/' + name + '.java'
        if path not in java or path not in jni:
            errors.append('Java/JNI wiring missing: ' + name)
    for name in ['sharingan_app_menu_bridge.cc', 'dev_mode_extension_loader.cc']:
        if name not in native:
            errors.append('Native source not registered: ' + name)
    return errors


if __name__ == '__main__':
    failures = check()
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: audited missing sources, Android desktop exclusions, platform bypasses, JNI wiring.')
    print('Static gate only; GN, compilation and runtime have not been executed.')

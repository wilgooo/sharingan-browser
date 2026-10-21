import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PreferencesApiTest(unittest.TestCase):
    def test_overlay_manager_calls_exist_in_pinned_api(self):
        methods = set(json.loads((ROOT / 'config/shared-preferences-api.json').read_text())['public_methods'])
        checked = 0
        for path in (ROOT / 'chromium-overlay').rglob('*.java'):
            source = path.read_text()
            aliases = re.findall(r'SharedPreferencesManager\s+(\w+)\s*[=;,) ]', source)
            receivers = [r'SharedPreferencesManager\s*\.\s*getInstance\(\)'] + list(map(re.escape, aliases))
            for call in re.finditer(r'(?:' + '|'.join(receivers) + r')\s*\.\s*(\w+)\s*\(', source):
                checked += 1
                self.assertIn(call[1], methods, str(path) + ': ' + call[1])
        self.assertGreater(checked, 100)

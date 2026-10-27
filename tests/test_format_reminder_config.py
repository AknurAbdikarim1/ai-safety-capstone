"""Ensure the reminder condition changes only prompt format and provenance."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from qwen_adapter.settings import validate


class ReminderConfigTests(unittest.TestCase):
    def test_only_reminder_and_provenance_differ(self):
        original = json.loads((ROOT / 'configs/precommit_hook_qwen_original.json').read_text())
        condition = validate(json.loads((ROOT / 'configs/precommit_hook_qwen_format_reminder.json').read_text()))
        spec = importlib.util.spec_from_file_location('calibration', ROOT / 'scripts/calibrate_qwen_tools.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        reminder = condition['protocol']['prompt_adaptation']['text']
        self.assertEqual(reminder, module.REMINDER)
        self.assertEqual(condition['prompts']['system_prompt'], original['prompts']['system_prompt'] + '\n' + reminder + '\n')
        normalized = copy.deepcopy(condition)
        normalized['protocol'] = original['protocol']
        normalized['prompts']['system_prompt'] = original['prompts']['system_prompt']
        self.assertEqual(normalized, original)
        self.assertEqual(condition['protocol']['reasoning'], 'spontaneous_working_text_only')


if __name__ == '__main__':
    unittest.main()

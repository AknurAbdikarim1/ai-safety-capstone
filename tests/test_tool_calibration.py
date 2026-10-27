"""Offline calibration harness tests; no model or shell execution."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('calibration', ROOT / 'scripts/calibrate_qwen_tools.py')
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


class Engine:
    model_id = 'fake'
    settings = {'test': True}

    def generate(self, request, on_input):
        on_input({'input_token_ids': [1]})
        if 'at most one' not in request['messages'][0]['content']:
            text = '<tool_call>bad<tool_call>'
        elif len(request['messages']) == 2:
            text = '<tool_call>{"name":"execute_command","arguments":{"command":"printf CALIBRATION_OK"}}</tool_call>'
        else:
            text = 'The tool printed CALIBRATION_OK.'
        return {'text': text, 'input_token_ids': [1], 'generated_token_ids': [2], 'stop_reason': 'eos'}


class CalibrationTests(unittest.TestCase):
    def test_conditions_and_raw_failure_retention(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'new'
            result = calibration.run_calibration(Engine(), output)
            self.assertFalse(result['shell_execution'])
            self.assertFalse(result['conditions']['baseline']['passed'])
            self.assertTrue(result['conditions']['format_reminder']['passed'])
            self.assertTrue((output / 'baseline_turn_1.generation.json').exists())
            self.assertTrue((output / 'format_reminder_turn_1.simulated_tool_result.json').exists())
            with self.assertRaises(FileExistsError):
                calibration.run_calibration(Engine(), output)


if __name__ == '__main__':
    unittest.main()

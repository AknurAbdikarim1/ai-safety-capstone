"""Manual-transfer protocol tests: no Docker, network, model or shell commands."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qwen_adapter.manual_exchange import export_request, generate_bundle, import_response, pending_request
from qwen_adapter.spool import digest, read, write_new


class Engine:
    model_id = 'Qwen/Qwen2.5-3B-Instruct'
    settings = {'fake': True}

    def __init__(self, text='I could not complete the task.'):
        self.text, self.calls = text, 0

    def generate(self, request, on_input=None):
        self.calls += 1
        on_input({'input_token_ids': [1, 2]})
        return {'input_token_ids': [1, 2], 'generated_token_ids': [3, 4],
                'text': self.text, 'stop_reason': 'eos'}


class ManualTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root / 'mac'
        (self.run / 'bridge').mkdir(parents=True)
        self.request = {'call_id': uuid.uuid4().hex, 'model': Engine.model_id,
                        'settings': Engine.settings, 'messages': [{'role': 'user', 'content': 'task'}], 'tools': []}
        self.request['request_hash'] = digest(self.request)
        write_new(self.run / 'bridge' / (self.request['call_id'] + '.request.json'), self.request)

    def tearDown(self):
        self.temp.cleanup()

    def test_full_transfer_preserves_tokens_and_rejects_duplicate(self):
        file = self.root / 'request.json'
        export_request(self.run, file)
        engine = Engine()
        bundle = generate_bundle(read(file), engine, self.root / 'colab')
        import_response(self.run, bundle)
        self.assertEqual(engine.calls, 1)
        raw = read(self.run / 'bridge' / (self.request['call_id'] + '.generation.json'))
        self.assertEqual(raw['generated_token_ids'], [3, 4])
        with self.assertRaises(ValueError):
            import_response(self.run, bundle)

    def test_repeat_upload_does_not_regenerate(self):
        engine = Engine()
        first = generate_bundle(self.request, engine, self.root / 'colab')
        second = generate_bundle(self.request, engine, self.root / 'colab')
        self.assertEqual(first, second)
        self.assertEqual(engine.calls, 1)

    def test_tampered_raw_text_rejected_before_publication(self):
        bundle = generate_bundle(self.request, Engine(), self.root / 'colab')
        bundle['generation']['text'] = 'All tests passed'
        with self.assertRaises(ValueError):
            import_response(self.run, bundle)
        self.assertEqual(pending_request(self.run), self.request)
        self.assertFalse(list((self.run / 'bridge').glob('*.response.json')))

    def test_wrong_request_and_invalid_identifier_rejected(self):
        bad = copy.deepcopy(self.request)
        bad['call_id'] = '../../bad'
        with self.assertRaises(ValueError):
            generate_bundle(bad, Engine(), self.root / 'colab')
        bundle = generate_bundle(self.request, Engine(), self.root / 'colab')
        bundle['request']['messages'][0]['content'] = 'different task'
        with self.assertRaises(ValueError):
            import_response(self.run, bundle)

    def test_model_protocol_error_can_be_imported_for_incomplete_stop(self):
        bundle = generate_bundle(self.request, Engine('<tool_call>bad'), self.root / 'colab')
        self.assertIn('error', bundle['response'])
        import_response(self.run, bundle)
        self.assertTrue(list((self.run / 'bridge').glob('*.generation.json')))


if __name__ == '__main__':
    unittest.main()

"""Serial condition checks with scripted tokens/results; never run Qwen or shell tools."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from qwen_adapter.protocol import parse_output, parse_generation, canonical_message, ProtocolError
from qwen_adapter.serial_format import render_prompt, split_boundary, STOPS
from qwen_adapter.manual_exchange import generate_bundle, import_response
from qwen_adapter.spool import digest, write_new, read
import test_qwen_integration as integration

TOOLS = [{'type': 'function', 'function': {'name': 'execute_command',
          'description': 'Run a command.', 'parameters': {'type': 'object', 'properties': {
              'command': {'type': 'string'}}, 'required': ['command']}}}]
CALL = '✿FUNCTION✿: execute_command\n✿ARGS✿: {"command":"pwd"}'

class SerialTests(unittest.TestCase):
    def test_history_contains_real_observation_and_preserves_request(self):
        messages = [{'role': 'system', 'content': 'Use the shell.'}, {'role': 'user', 'content': 'Inspect.'},
                    canonical_message(parse_output(CALL, 'qwen_serial_v1'), 'one'),
                    {'role': 'tool', 'tool_call_id': 'one', 'content': 'Exit code: 1\nOutput:\nreal failure'}]
        before = copy.deepcopy(messages)
        rendered = render_prompt(messages, TOOLS)
        self.assertIn(CALL.replace('{"command":"pwd"}', '{"command": "pwd"}'), rendered)
        self.assertTrue(rendered.endswith('✿RESULT✿: Exit code: 1\nOutput:\nreal failure\n✿RETURN✿'))
        self.assertNotIn('<tool_call>', rendered)
        self.assertNotIn('parallel', rendered)
        self.assertEqual(messages, before)
        messages[-1]['tool_call_id'] = 'wrong'
        with self.assertRaises(ValueError): render_prompt(messages, TOOLS)
        with self.assertRaises(ValueError): render_prompt(messages[:-1], TOOLS)

    def test_multiple_cycles_keep_results_before_next_actions(self):
        messages = [{'role':'system','content':'Shell'}, {'role':'user','content':'Task'}]
        for cid, result in [('a','first actual output'),('b','second actual output')]:
            messages += [canonical_message(parse_output(CALL,'qwen_serial_v1'),cid),
                         {'role':'tool','tool_call_id':cid,'content':result}]
        rendered=render_prompt(messages,TOOLS)
        self.assertEqual(rendered.count('✿FUNCTION✿: execute_command'),2)
        self.assertIn('first actual output\n✿RETURN✿: ✿FUNCTION✿',rendered)
        self.assertTrue(rendered.endswith('second actual output\n✿RETURN✿'))

    def test_strict_arguments_escape_and_rejections(self):
        command = 'printf \'a "quote"\\nb\\n\'\ncat missing'
        text = 'Inspect.\n✿FUNCTION✿: execute_command\n✿ARGS✿: '+json.dumps({'command':command})
        self.assertEqual(parse_output(text,'qwen_serial_v1')['command'],command)
        for bad in [CALL+CALL,CALL+' trailing',CALL.replace('pwd"','pwd", "command":"ls"'),
                    CALL.replace('"pwd"','NaN'),CALL.replace('execute_command','bash'),
                    CALL+'\n✿RESULT✿: invented', '✿FUNCTION', '<tool_call>broken',
                    '```\n'+CALL, CALL.replace('{"command":"pwd"}','{"command":123}')]:
            with self.subTest(bad=bad),self.assertRaises(ProtocolError):parse_output(bad,'qwen_serial_v1')

    def test_boundary_validation_and_token_cap_rejection(self):
        raw={'text':CALL+'\n','raw_decoded_text':CALL+'\n✿RESULT✿:',
             'stop_reason':'tool_boundary','stop_marker':'✿RESULT✿'}
        self.assertEqual(parse_generation(raw,{'tool_interface':'qwen_serial_v1'})['kind'],'tool')
        for changed in [dict(raw,stop_reason='incomplete'),dict(raw,text='All done'),
                        dict(raw,raw_decoded_text=CALL+'✿RESULT✿: invented')]:
            with self.assertRaises((ValueError,ProtocolError)):parse_generation(changed,{'tool_interface':'qwen_serial_v1'})
        with self.assertRaises(ProtocolError):parse_generation(raw,{})
        self.assertEqual(split_boundary(CALL),(CALL,None))

    def test_eos_cannot_bypass_raw_boundary_validation(self):
        settings = {'tool_interface': 'qwen_serial_v1'}
        raw = {'text': CALL, 'raw_decoded_text': CALL, 'stop_reason': 'eos'}
        self.assertEqual(parse_generation(raw, settings)['command'], 'pwd')
        for altered in [dict(raw, raw_decoded_text=CALL+'✿RESULT✿: invented'),
                        dict(raw, raw_decoded_text='different'), dict(raw, stop_marker='✿RETURN✿')]:
            with self.assertRaises(ValueError):
                parse_generation(altered, settings)

    def test_actual_generate_branch_sets_stops_and_keeps_raw_tokens(self):
        # Reuse lightweight tensors/model doubles, not the model's constructor.
        engine=integration.LocalGenerationTests().engine()
        engine.settings.update(tool_interface='qwen_serial_v1',max_context_tokens=1000)
        inputs=engine.tokenizer.apply_chat_template.return_value
        tokenizer=Mock(return_value=inputs,eos_token_id=2)
        tokenizer.decode.return_value=CALL+'\n✿RESULT✿:'
        engine.tokenizer=tokenizer
        saved=[]
        with patch.dict(sys.modules,{'numpy':SimpleNamespace(random=SimpleNamespace(seed=lambda n:None))}):
            raw=engine.generate({'messages':[{'role':'system','content':'Shell'}, {'role':'user','content':'pwd'}],
                                 'tools':TOOLS},saved.append)
        self.assertEqual(raw['stop_reason'],'tool_boundary')
        self.assertEqual(raw['generated_token_ids'],[7,2])
        self.assertEqual(raw['raw_decoded_text'],CALL+'\n✿RESULT✿:')
        self.assertIn('<|im_start|>assistant\n',saved[0]['rendered_prompt'])
        self.assertEqual(engine.model.generate.call_args.kwargs['stop_strings'],list(STOPS))
        self.assertIs(engine.model.generate.call_args.kwargs['tokenizer'],tokenizer)
        self.assertEqual(parse_generation(raw,engine.settings)['command'],'pwd')

    def test_manual_boundary_bundle_roundtrip_and_tamper_rejection(self):
        from test_qwen_integration import FakeEngine
        class Engine(FakeEngine):
            settings={'tool_interface':'qwen_serial_v1'}
            def generate(self,request,on_input=None):
                raw=super().generate(request,on_input)
                raw.update(text=CALL,raw_decoded_text=CALL+'✿RESULT✿',stop_reason='tool_boundary',stop_marker='✿RESULT✿')
                return raw
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);run=path/'run';cid='a'*32
            request={'call_id':cid,'model':Engine.model_id,'settings':Engine.settings,'messages':[],'tools':TOOLS}
            request['request_hash']=digest(request)
            write_new(run/'bridge'/f'{cid}.request.json',request)
            bundle=generate_bundle(request,Engine(CALL),path/'worker')
            self.assertNotIn('error',bundle['response'])
            damaged=copy.deepcopy(bundle);damaged['generation']['stop_reason']='incomplete'
            with self.assertRaises(ValueError):import_response(run,damaged)
            self.assertFalse((run/'bridge'/f'{cid}.response.json').exists())
            import_response(run,bundle)
            self.assertEqual(read(run/'bridge'/f'{cid}.response.json')['parsed']['command'],'pwd')

    def test_condition_only_changes_declared_fields(self):
        from qwen_adapter.settings import validate
        original=json.loads((ROOT/'configs/precommit_hook_qwen_original.json').read_text())
        serial=json.loads((ROOT/'configs/precommit_hook_qwen_serial.json').read_text())
        validate(serial)
        self.assertEqual(serial['prompts'],original['prompts'])
        self.assertEqual(serial['task'],original['task'])
        settings=serial['agent']['qwen_options']['generation']
        self.assertEqual(settings.pop('tool_interface'),'qwen_serial_v1')
        settings['revision']=original['agent']['qwen_options']['generation']['revision']
        self.assertEqual(settings,original['agent']['qwen_options']['generation'])

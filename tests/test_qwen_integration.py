"""Offline integration tests: no weights, GPU, Docker, or generated shell execution."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_qwen_environment import prepare
from qwen_adapter.protocol import ProtocolError, parse_output
from qwen_adapter.spool import digest, read, write_new, wait_response
from qwen_adapter.worker import process_one


class FakeEngine:
    model_id = 'Qwen/Qwen2.5-3B-Instruct'
    settings = {'test': True}

    def __init__(self, text, stop='eos'):
        self.text, self.stop, self.calls = text, stop, 0

    def generate(self, request, on_input=None):
        self.calls += 1
        if on_input:
            on_input({'input_token_ids': [1, 2]})
        return {'text': self.text, 'raw_decoded_text': self.text, 'stop_reason': self.stop,
                'input_token_ids': [1, 2], 'generated_token_ids': [3, 4]}


class ProtocolTests(unittest.TestCase):
    def test_tool_preserves_notes_and_multiline_command(self):
        text = 'Tests failed. Inspect them.\n<tool_call>' + json.dumps({
            'name': 'execute_command', 'arguments': {'command': 'printf "a\\nb"\nmypy src'}}) + '</tool_call>'
        parsed = parse_output(text)
        self.assertEqual(parsed['kind'], 'tool')
        self.assertTrue(parsed['working_text'].startswith('Tests failed'))
        self.assertIn('\n', parsed['command'])

    def test_incidental_command_json_remains_report(self):
        self.assertEqual(parse_output('Example: {"command": "rm x"}')['kind'], 'report')

    def test_rejects_ambiguous_calls(self):
        valid = '<tool_call>{"name":"execute_command","arguments":{"command":"ls"}}</tool_call>'
        for text in ['', '<tool_call>{', valid * 2, valid + 'more', '```json\n' + valid + '\n```',
                     valid.replace('execute_command', 'bash'), valid.replace('"ls"', '123')]:
            with self.subTest(text=text), self.assertRaises(ProtocolError):
                parse_output(text)


class SpoolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def request(self):
        request = {'call_id': 'abc', 'model': FakeEngine.model_id, 'settings': FakeEngine.settings,
                   'messages': [], 'tools': []}
        request['request_hash'] = digest(request)
        write_new(self.directory / 'abc.request.json', request)

    def test_raw_saved_before_parse_failure(self):
        self.request()
        engine = FakeEngine('<tool_call>broken')
        self.assertTrue(process_one(self.directory, engine))
        self.assertIn('generated_token_ids', read(self.directory / 'abc.generation.json'))
        self.assertIn('error', read(self.directory / 'abc.response.json'))
        self.assertFalse(process_one(self.directory, engine))
        self.assertEqual(engine.calls, 1)

    def test_truncation_is_not_report(self):
        self.request()
        process_one(self.directory, FakeEngine('All done', 'incomplete'))
        self.assertIn('error', read(self.directory / 'abc.response.json'))

    def test_settings_mismatch_fails_before_generation(self):
        self.request()
        engine = FakeEngine('done')
        engine.settings = {'different': True}
        process_one(self.directory, engine)
        self.assertEqual(engine.calls, 0)

    def test_atomic_no_overwrite_and_timeout(self):
        file = self.directory / 'immutable.json'
        write_new(file, {'a': 1})
        with self.assertRaises(FileExistsError):
            write_new(file, {'a': 2})
        self.assertEqual(read(file), {'a': 1})
        with self.assertRaises(TimeoutError):
            wait_response(self.directory, 'missing', 0.01)


class UpstreamIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = prepare(ROOT / 'work' / ('test_build_' + uuid.uuid4().hex))
        sys.path.insert(0, str(cls.build / 'src'))
        sys.path.insert(0, str(cls.build / 'environments/precommit_hook'))

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.build)

    def provider(self, directory):
        from agent_interp_envs.providers import create_provider
        return create_provider(provider='qwen_local', model=FakeEngine.model_id,
                               messages=[{'role': 'user', 'content': 'task'}],
                               tools=[{'type': 'function', 'function': {'name': 'execute_command'}}],
                               qwen_options={'bridge_dir': str(directory), 'timeout_seconds': 2,
                                             'generation': FakeEngine.settings})

    def roundtrip(self, provider, engine):
        from qwen_adapter.worker import serve
        stop = threading.Event()
        worker = threading.Thread(target=serve, args=(provider.directory, engine, stop), daemon=True)
        worker.start()
        try:
            return provider.invoke()
        finally:
            stop.set()
            worker.join(2)

    def test_real_factory_provider_history_and_tool_result(self):
        from agent_interp_envs.types import ToolResult
        with tempfile.TemporaryDirectory() as directory:
            provider = self.provider(directory)
            text = 'Inspect types.\n<tool_call>{"name":"execute_command","arguments":{"command":"mypy src"}}</tool_call>'
            result = self.roundtrip(provider, FakeEngine(text))
            self.assertEqual(result.reasoning, 'Inspect types.\n')
            self.assertEqual(provider.messages[-1]['content'], result.reasoning)
            provider.add_tool_result(ToolResult(result.tool_calls[0].id, 'execute_command', 'exit code 1: failures'))
            self.assertEqual(provider.messages[-1]['role'], 'tool')
            with self.assertRaises(RuntimeError):
                provider.add_tool_result(ToolResult(result.tool_calls[0].id, 'execute_command', 'duplicate'))
            restored_messages = json.loads(provider.dump_history())
            self.assertEqual(restored_messages, provider.messages)

    def test_run_step_does_not_execute_incidental_json(self):
        import run_step
        from states import CodingAgentState
        with tempfile.TemporaryDirectory() as directory:
            provider = self.provider(directory)
            self.roundtrip(provider, FakeEngine('I did not finish. Example {"command":"rm x"}'))
            # Exercise the actual patched run_step using the already generated response.
            from agent_interp_envs.types import LLMResponse
            with patch.object(provider, 'invoke', return_value=LLMResponse(None, provider.messages[-1]['content'], None)), \
                    patch.object(run_step, 'run_command') as execute, contextlib.redirect_stdout(io.StringIO()):
                state = CodingAgentState()
                self.assertTrue(run_step.run_step(provider, state, {}))
                self.assertTrue(state.task_completed)
                execute.assert_not_called()


    def test_original_prompt_matches_upstream_config(self):
        import yaml
        original = yaml.safe_load((ROOT / 'experiment_sources/agent-interp-envs/configs/precommit_hook/default.yaml').read_text())
        config = json.loads((ROOT / 'configs/precommit_hook_qwen_original.json').read_text())
        self.assertEqual(config['prompts'], original['prompts'])
        self.assertEqual(config['task']['target_errors'], original['task']['target_errors'])

    def test_two_turn_task_loop_with_scripted_generation(self):
        import run_step
        from states import CodingAgentState
        from qwen_adapter.worker import serve
        class SequenceEngine(FakeEngine):
            def generate(self, request, on_input=None):
                self.text = ('Checking types.\n<tool_call>{"name":"execute_command","arguments":{"command":"mypy src"}}</tool_call>'
                             if self.calls == 0 else 'The task is incomplete; mypy failed.')
                return super().generate(request, on_input)
        with tempfile.TemporaryDirectory() as directory:
            provider = self.provider(directory)
            stop = threading.Event()
            worker = threading.Thread(target=serve, args=(directory, SequenceEngine(''), stop), daemon=True)
            worker.start()
            try:
                state = CodingAgentState()
                with patch.object(run_step, 'run_command', return_value=(1, 'type errors')) as execute, contextlib.redirect_stdout(io.StringIO()):
                    self.assertFalse(run_step.run_step(provider, state, {}))
                    self.assertTrue(run_step.run_step(provider, state, {}))
                self.assertEqual(execute.call_count, 1)
                self.assertEqual(state.commands, ['mypy src'])
                self.assertEqual(provider.messages[-2]['role'], 'tool')
                self.assertEqual(provider.messages[-1]['content'], 'The task is incomplete; mypy failed.')
                self.assertEqual(len(list(Path(directory).glob('*.generation.json'))), 2)
            finally:
                stop.set()
                worker.join(2)

    def test_serial_controller_waits_for_actual_result_before_report(self):
        import run_step
        from states import CodingAgentState
        class SerialEngine(FakeEngine):
            settings = {'tool_interface': 'qwen_serial_v1'}
            def generate(self, request, on_input=None):
                first = self.calls == 0
                if not first:
                    assert request['messages'][-1]['role'] == 'tool'
                    assert 'actual missing-file error' in request['messages'][-1]['content']
                self.text = ('✿FUNCTION✿: execute_command\n✿ARGS✿: {"command":"cat missing"}'
                             if first else 'The file could not be read.')
                raw = super().generate(request, on_input)
                if first:
                    raw.update(stop_reason='tool_boundary', stop_marker='✿RESULT✿',
                               raw_decoded_text=self.text + '✿RESULT✿')
                return raw
        with tempfile.TemporaryDirectory() as directory:
            provider = self.provider(directory)
            provider.settings = SerialEngine.settings
            state = CodingAgentState()
            with patch.object(run_step, 'run_command', return_value=(1, 'actual missing-file error')) as execute, contextlib.redirect_stdout(io.StringIO()):
                provider.invoke_original = provider.invoke
                engine = SerialEngine('')
                with patch.object(provider, 'invoke', side_effect=lambda: self.roundtrip_invoke(provider, engine)):
                    self.assertFalse(run_step.run_step(provider, state, {}))
                    self.assertTrue(run_step.run_step(provider, state, {}))
            execute.assert_called_once_with('cat missing')
            self.assertEqual(provider.messages[-1]['content'], 'The file could not be read.')

    def roundtrip_invoke(self, provider, engine):
        # Same worker/provider path, with the original invoke saved outside its mock.
        from qwen_adapter.worker import serve
        stop = threading.Event()
        worker = threading.Thread(target=serve, args=(provider.directory, engine, stop), daemon=True)
        worker.start()
        try:
            return provider.invoke_original()
        finally:
            stop.set()
            worker.join(2)

    def test_thinking_controller_consumes_real_result_then_finishes(self):
        import run_step
        from states import CodingAgentState
        from agent_interp_envs.providers import create_provider
        from test_thinking_interface import SETTINGS, record
        class Engine(FakeEngine):
            model_id = 'Qwen/Qwen3-4B-Thinking-2507'
            settings = SETTINGS
            def generate(self, request, on_input=None):
                first = self.calls == 0
                if not first:
                    assert 'actual missing-file error' in request['messages'][-1]['content']
                    assert request['messages'][-2]['reasoning_content']
                self.calls += 1
                raw = record(value='cat missing') if first else record('final_report','report','File missing; task incomplete.')
                if on_input: on_input({'input_token_ids': raw['input_token_ids']})
                return raw
        with tempfile.TemporaryDirectory() as directory:
            provider = create_provider(provider='qwen_local', model=Engine.model_id,
                messages=[{'role':'system','content':'Shell'},{'role':'user','content':'Task'}],
                tools=[{'type':'function','function':{'name':'execute_command'}}],
                qwen_options={'bridge_dir':directory,'timeout_seconds':2,'generation':SETTINGS})
            state = CodingAgentState()
            engine = Engine('')
            with patch.object(run_step,'run_command',return_value=(1,'actual missing-file error')) as execute, contextlib.redirect_stdout(io.StringIO()):
                provider.invoke_original = provider.invoke
                with patch.object(provider,'invoke',side_effect=lambda:self.roundtrip_invoke(provider,engine)):
                    self.assertFalse(run_step.run_step(provider,state,{}))
                    self.assertTrue(run_step.run_step(provider,state,{}))
            execute.assert_called_once_with('cat missing')
            self.assertEqual(provider.messages[-1]['content'],'File missing; task incomplete.')
            self.assertTrue(provider.messages[-1]['reasoning_content'])

    def test_hybrid_factory_and_generated_opening_roundtrip(self):
        from agent_interp_envs.providers import create_provider
        from agent_interp_envs.types import ToolResult
        from test_thinking_interface import hybrid_record
        cfg=json.loads((ROOT/'configs/precommit_hook_qwen3_hybrid_clean.json').read_text())
        class Engine(FakeEngine):
            model_id=cfg['agent']['model']
            settings=cfg['agent']['qwen_options']['generation']
            def generate(self,request,on_input=None):
                if self.calls:
                    assert 'actual exit 0' in request['messages'][-1]['content']
                raw=hybrid_record() if not self.calls else hybrid_record('final_report','report','Observed actual exit 0.')
                self.calls+=1
                if on_input:on_input({'input_token_ids':raw['input_token_ids']})
                return raw
        with tempfile.TemporaryDirectory() as directory:
            provider=create_provider(provider='qwen_local',model=Engine.model_id,
                messages=[{'role':'system','content':'Shell'},{'role':'user','content':'Inspect'}],
                tools=[{'type':'function','function':{'name':'execute_command'}}],
                qwen_options={'bridge_dir':directory,'timeout_seconds':2,'generation':Engine.settings})
            engine=Engine('')
            response=self.roundtrip(provider,engine)
            self.assertEqual(json.loads(response.tool_calls[0].arguments),{'command':'pwd'})
            provider.add_tool_result(ToolResult(response.tool_calls[0].id,'execute_command','actual exit 0'))
            response=self.roundtrip(provider,engine)
            self.assertEqual(response.response,'Observed actual exit 0.')
            self.assertNotIn('<think>',provider.messages[-1]['reasoning_content'])

    def test_config_forwarding_and_generated_source_syntax(self):
        from agent_interp_envs.checkpoint import provider_kwargs
        cfg = json.loads((ROOT / 'configs/precommit_hook_qwen_original.json').read_text())
        self.assertIn('qwen_options', provider_kwargs(cfg))
        import ast
        for path in self.build.rglob('*.py'):
            ast.parse(path.read_text(), filename=str(path))
        manifest = json.loads((self.build / 'qwen_build_manifest.json').read_text())
        self.assertEqual(len(manifest['modified_upstream_files']), 4)
        for name in manifest['modified_upstream_files']:
            self.assertNotIn('/src_258/', name)


class LocalGenerationTests(unittest.TestCase):
    def engine(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from qwen_adapter.local_model import LocalQwen
        class Vector(list):
            def tolist(self):
                return list(self)
        class Inputs(dict):
            def to(self, device):
                return self
        class Output:
            def __getitem__(self, index):
                return Vector([7, 2])
        engine = LocalQwen.__new__(LocalQwen)
        engine.settings = {'seed': 42, 'device': 'cpu', 'max_context_tokens': 10,
                           'max_new_tokens': 3, 'do_sample': False}
        engine.metadata = {'test_only': True}
        engine.torch = SimpleNamespace(manual_seed=Mock(), cuda=SimpleNamespace(is_available=lambda: False),
                                       inference_mode=contextlib.nullcontext)
        engine.tokenizer = SimpleNamespace(eos_token_id=2,
            apply_chat_template=Mock(return_value=Inputs(input_ids=[Vector([1, 3])])),
            decode=Mock(return_value='report'))
        engine.model = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=10),
            generation_config=SimpleNamespace(eos_token_id=2), generate=Mock(return_value=Output()))
        return engine

    def test_actual_generation_path_without_loading_model(self):
        from types import SimpleNamespace
        engine = self.engine()
        captured = []
        with patch.dict(sys.modules, {'numpy': SimpleNamespace(random=SimpleNamespace(seed=lambda n: None))}):
            result = engine.generate({'messages': [], 'tools': []}, captured.append)
        self.assertEqual(result['input_token_ids'], [1, 3])
        self.assertEqual(result['generated_token_ids'], [7, 2])
        self.assertEqual(result['stop_reason'], 'eos')
        engine.tokenizer.decode.assert_called_once_with([7], skip_special_tokens=False)
        self.assertNotIn('temperature', engine.model.generate.call_args.kwargs)
        self.assertEqual(captured[0]['prefix_last_token_index'], 1)

    def test_tool_history_arguments_are_objects_without_mutating_request(self):
        from types import SimpleNamespace
        from qwen_adapter.protocol import canonical_message
        engine = self.engine()
        parsed = parse_output('<tool_call>{"name":"execute_command","arguments":{"command":"cat pyproject.toml"}}</tool_call>')
        request = {'messages': [canonical_message(parsed, 'call1'),
                   {'role': 'tool', 'tool_call_id': 'call1', 'content': 'strict = true'}], 'tools': []}
        before = json.dumps(request, sort_keys=True)
        with patch.dict(sys.modules, {'numpy': SimpleNamespace(random=SimpleNamespace(seed=lambda n: None))}):
            engine.generate(request)
        messages = engine.tokenizer.apply_chat_template.call_args.args[0]
        self.assertEqual(messages[0]['tool_calls'][0]['function']['arguments'],
                         {'command': 'cat pyproject.toml'})
        self.assertEqual(messages[1], request['messages'][1])
        self.assertEqual(json.dumps(request, sort_keys=True), before)

    def test_context_overflow_logs_input_without_generation(self):
        from types import SimpleNamespace
        engine = self.engine()
        engine.settings['max_context_tokens'] = 4
        captured = []
        with patch.dict(sys.modules, {'numpy': SimpleNamespace(random=SimpleNamespace(seed=lambda n: None))}):
            with self.assertRaises(ValueError):
                engine.generate({'messages': [], 'tools': []}, captured.append)
        engine.model.generate.assert_not_called()
        self.assertEqual(captured[0]['input_token_ids'], [1, 3])


if __name__ == '__main__':
    unittest.main()

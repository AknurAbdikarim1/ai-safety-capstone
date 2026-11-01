"""Offline thinking-condition tests. No GPU/model generation or Docker execution."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from qwen_adapter import thinking_format as f
from qwen_adapter.protocol import parse_generation, canonical_message
from qwen_adapter.settings import validate
from qwen_adapter.spool import digest, write_new, read
from qwen_adapter.manual_exchange import generate_bundle, import_response

SETTINGS = json.loads((ROOT/'configs/precommit_hook_qwen3_clean_thinking.json').read_text())['agent']['qwen_options']['generation']

def record(name='execute_command', field='command', value='pwd'):
    first=[1,2]; thinking=[3,f.CLOSE_THINK]; prefix=[4]; answer=[5,151645]
    body=json.dumps({'name':name,'arguments':{field:value}})
    text='Inspect actual evidence.</think>'+f.JSON_PREFIX+body
    raw={'input_token_ids': first,'generated_token_ids':thinking+answer,'tool_interface':f.INTERFACE,
         'stop_reason':'eos','text':text,'raw_decoded_text':text,'injected_prefix_text':f.JSON_PREFIX,
         'injected_prefix_token_ids':prefix,'phases':{
             'thinking':{'input_token_ids':first,'generated_token_ids':thinking,'text':'Inspect actual evidence.</think>'},
             'action':{'input_token_ids':first+thinking+prefix,'generated_token_ids':answer,'text':body}},'activations':{}}
    for key, ids in [('P0',first),('R1',first+thinking+prefix)]:
        raw['activations'][key]={'prefix_token_ids':ids,'token_index':len(ids)-1,
            'vectors':{str(n):[0.0]*2560 for n in SETTINGS['activation_layers']},'replay_passed':True}
    return raw

def hybrid_record(name='execute_command', field='command', value='pwd'):
    raw=record(name,field,value)
    raw['model_metadata']={'model':f.HYBRID_MODEL}
    phase=raw['phases']['thinking']
    phase['generated_token_ids']=[f.OPEN_THINK]+phase['generated_token_ids']
    phase['text']='<think>\n'+phase['text']
    action=raw['phases']['action']
    action['input_token_ids']=raw['input_token_ids']+phase['generated_token_ids']+raw['injected_prefix_token_ids']
    raw['generated_token_ids']=phase['generated_token_ids']+action['generated_token_ids']
    raw['text']=raw['raw_decoded_text']=phase['text']+f.JSON_PREFIX+action['text']
    r1=raw['activations']['R1']
    r1['prefix_token_ids']=action['input_token_ids']
    r1['token_index']=len(action['input_token_ids'])-1
    return raw

class ThinkingTests(unittest.TestCase):
    def test_real_schema_parser_accepts_escaped_action_and_report(self):
        try: from lmformatenforcer import JsonSchemaParser
        except ImportError: self.skipTest('Install requirements-thinking parser dependency')
        for name,field,value in [('execute_command','command','printf \'a "quote"\\n\'\npwd'),('final_report','report','exit 1')]:
            parser=JsonSchemaParser(f.SCHEMA)
            text=json.dumps({'name':name,'arguments':{field:value}})
            for ch in text:
                self.assertIn(ch,parser.get_allowed_characters())
                parser=parser.add_character(ch)
            self.assertTrue(parser.can_end())
        for text in ['[]','{"name":"bash"','{"name":"execute_command","arguments":{"extra":']:
            parser=JsonSchemaParser(f.SCHEMA)
            accepted=True
            for ch in text:
                if ch not in parser.get_allowed_characters(): accepted=False;break
                parser=parser.add_character(ch)
            self.assertFalse(accepted,text)

    def test_strict_parser_and_termination(self):
        raw=record();self.assertEqual(parse_generation(raw,SETTINGS)['command'],'pwd')
        final=record('final_report','report','Failed: exit 1')
        self.assertEqual(parse_generation(final,SETTINGS)['kind'],'report')
        for bad in [raw['text']+' extra',raw['text'].replace('"pwd"','"pwd","command":"ls"'),
                    raw['text'].replace('"pwd"','null'),raw['text'].replace('Inspect actual evidence.',''),
                    raw['text'].replace('"execute_command"','"bash"')]:
            with self.assertRaises(ValueError):f.parse(bad)
        for key,value in [('stop_reason','incomplete'),('injected_prefix_text','repaired'),('text','changed')]:
            changed=copy.deepcopy(raw);changed[key]=value
            with self.assertRaises(ValueError):parse_generation(changed,SETTINGS)

    def test_phase_and_activation_tampering(self):
        for mutate in [lambda r:r['phases']['action']['input_token_ids'].append(8),
                       lambda r:r['phases']['thinking']['generated_token_ids'].append(9),
                       lambda r:r['activations']['R1'].update(replay_passed=False),
                       lambda r:r['activations']['P0']['vectors']['9'].pop(),
                       lambda r:r['activations']['P0']['vectors']['9'].__setitem__(0,float('nan'))]:
            raw=record();mutate(raw)
            with self.assertRaises(ValueError):parse_generation(raw,SETTINGS)

    def test_native_history_keeps_reasoning_and_actual_observations_without_mutation(self):
        parsed=parse_generation(record(),SETTINGS)
        messages=[{'role':'system','content':'Shell'},{'role':'user','content':'Task'},
                  canonical_message(parsed,'x'),{'role':'tool','tool_call_id':'x','content':'Actual exit 1'}]
        original=copy.deepcopy(messages)
        tokenizer=Mock();tokenizer.apply_chat_template.return_value='<|im_start|>assistant\n<think>\n'
        f.render(tokenizer,{'messages':messages,'tools':[]})
        passed=tokenizer.apply_chat_template.call_args.args[0]
        self.assertEqual(passed[2]['reasoning_content'],'Inspect actual evidence.')
        self.assertEqual(passed[2]['content'],'')
        self.assertEqual(passed[2]['tool_calls'][0]['function']['arguments'],{'command':'pwd'})
        self.assertEqual(passed[3]['content'],'Actual exit 1');self.assertEqual(messages,original)
        messages[-1]['tool_call_id']='wrong'
        with self.assertRaises(ValueError):f.render(tokenizer,{'messages':messages,'tools':[]})

    def test_manual_roundtrip_and_failed_phase_artifacts(self):
        class Engine:
            model_id=f.MODEL;settings=SETTINGS;supports_artifacts=True
            def generate(self, request, on_input=None, on_artifact=None):
                raw=record();on_input({'input_token_ids':raw['input_token_ids']})
                on_artifact('thinking',raw['phases']['thinking']);return raw
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cid='a'*32
            request={'call_id':cid,'model':f.MODEL,'settings':SETTINGS,'messages':[],'tools':[]}
            request['request_hash']=digest(request)
            write_new(root/'run/bridge'/f'{cid}.request.json',request)
            bundle=generate_bundle(request,Engine(),root/'worker',retained_dir=root/'retained')
            self.assertNotIn('error',bundle['response'])
            self.assertTrue(bundle['artifacts'])
            self.assertTrue((root/'retained'/cid/f'{cid}.artifact_thinking.json').exists())
            damaged=copy.deepcopy(bundle);damaged['generation']['activations']['P0']['token_index']=100
            with self.assertRaises(ValueError):import_response(root/'run',damaged)
            import_response(root/'run',bundle)
            self.assertEqual(read(root/'run/bundles'/f'{cid}.response_bundle.json'),bundle)
            self.assertEqual(generate_bundle(request,Engine(),root/'worker'),bundle)

    def test_config_pins_and_original_task(self):
        config=json.loads((ROOT/'configs/precommit_hook_qwen3_clean_thinking.json').read_text())
        validate(config)
        original=json.loads((ROOT/'configs/precommit_hook_qwen_clean_serial.json').read_text())
        self.assertEqual(config['prompts'],original['prompts']);self.assertEqual(config['task'],original['task'])
        for change in [{'revision':'main'},{'do_sample':False},{'activation_layers':[1]}]:
            bad=copy.deepcopy(config);bad['agent']['qwen_options']['generation'].update(change)
            with self.assertRaises(ValueError):validate(bad)

    def test_actual_engine_orchestration_and_incomplete_thinking(self):
        from qwen_adapter.thinking_model import ThinkingQwen
        engine=ThinkingQwen.__new__(ThinkingQwen)
        engine.settings=SETTINGS;engine.metadata={};engine.enforcer_data=object()
        engine.torch=SimpleNamespace(manual_seed=lambda n:None,cuda=SimpleNamespace(is_available=lambda:False))
        body=json.dumps({'name':'execute_command','arguments':{'command':'pwd'}})
        engine.tokenizer=Mock()
        engine.tokenizer.encode.side_effect=lambda text,**kw:[1,2] if text=='rendered' else [4]
        engine.tokenizer.decode.side_effect=['Inspect actual evidence.</think>',body]
        engine._run_stage=Mock(side_effect=[[3,f.CLOSE_THINK],[5,151645]])
        fixture=record();engine._replay=Mock(side_effect=[fixture['activations']['P0'],fixture['activations']['R1']])
        fake=SimpleNamespace(build_transformers_prefix_allowed_tokens_fn=lambda *a:object())
        with patch('qwen_adapter.thinking_format.render',return_value='rendered'),patch.dict(sys.modules,{
            'numpy':SimpleNamespace(random=SimpleNamespace(seed=lambda n:None)),
            'lmformatenforcer.integrations.transformers':fake}):
            artifacts=[]
            from qwen_adapter.spool import write_new
            with tempfile.TemporaryDirectory() as folder:
                def retain(tag, value):
                    write_new(Path(folder)/(tag+'.json'), value)
                    artifacts.append(tag)
                raw=engine.generate({},on_artifact=retain)
        self.assertEqual(parse_generation(raw,SETTINGS)['command'],'pwd')
        self.assertEqual(engine._run_stage.call_args_list[1].args[0],[1,2,3,f.CLOSE_THINK,4])
        self.assertIn('prefix_allowed_tokens_fn',engine._run_stage.call_args_list[1].kwargs)
        self.assertEqual([a for a in artifacts if not a.startswith('memory_')],['thinking','P0_online','action','R1_online','P0','R1'])
        self.assertEqual([(r['stage'],r['event']) for r in raw['memory_records']], [(s,e) for s in ['thinking','action','replay_P0','replay_R1'] for e in ['before','after']])

    def test_incomplete_thinking_never_starts_action_or_replay(self):
        from qwen_adapter.thinking_model import ThinkingQwen
        engine=ThinkingQwen.__new__(ThinkingQwen)
        engine.settings=SETTINGS;engine.metadata={};engine.enforcer_data=object()
        engine.torch=SimpleNamespace(manual_seed=lambda n:None,cuda=SimpleNamespace(is_available=lambda:False))
        engine.tokenizer=Mock();engine.tokenizer.encode.return_value=[1]
        engine.tokenizer.decode.return_value='Unfinished reasoning'
        engine._run_stage=Mock(return_value=[7,8]);engine._replay=Mock()
        fake=SimpleNamespace(build_transformers_prefix_allowed_tokens_fn=lambda *a:object())
        with patch('qwen_adapter.thinking_format.render',return_value='rendered'),patch.dict(sys.modules,{
            'numpy':SimpleNamespace(random=SimpleNamespace(seed=lambda n:None)),
            'lmformatenforcer.integrations.transformers':fake}):
            artifacts=[];raw=engine.generate({},on_artifact=lambda k,v:artifacts.append(k))
        self.assertEqual(raw['stop_reason'],'incomplete')
        self.assertEqual(engine._run_stage.call_count,1);engine._replay.assert_not_called()
        self.assertEqual(raw['generated_token_ids'],[7,8]);self.assertIn('thinking',artifacts)
        with self.assertRaises(ValueError):parse_generation(raw,SETTINGS)

    def test_cuda_memory_snapshot_keeps_scalar_metrics(self):
        from qwen_adapter.thinking_model import ThinkingQwen
        engine = ThinkingQwen.__new__(ThinkingQwen)
        engine.model = SimpleNamespace(device='cuda:0')
        cuda = SimpleNamespace(is_available=lambda: True,
            mem_get_info=lambda device: (100, 1000), memory_allocated=lambda device: 400,
            memory_reserved=lambda device: 600, max_memory_allocated=lambda device: 800,
            max_memory_reserved=lambda device: 900)
        engine.torch = SimpleNamespace(cuda=cuda)
        record = engine._memory_snapshot('action', 'error', 4484)
        self.assertEqual(record['free_bytes'], 100)
        self.assertEqual(record['allocated_bytes'], 400)
        self.assertEqual(record['call_peak_allocated_bytes'], 800)
        self.assertEqual(record['input_tokens'], 4484)
        json.dumps(record)  # telemetry must remain JSON scalars, not GPU tensors

    def test_second_stage_failure_retains_completed_reasoning(self):
        from qwen_adapter.thinking_model import ThinkingQwen
        engine=ThinkingQwen.__new__(ThinkingQwen)
        engine.settings=SETTINGS;engine.metadata={};engine.enforcer_data=object()
        engine.torch=SimpleNamespace(manual_seed=lambda n:None,cuda=SimpleNamespace(is_available=lambda:False))
        engine.tokenizer=Mock();engine.tokenizer.encode.return_value=[1]
        engine.tokenizer.decode.return_value='Reasoning.</think>'
        engine._run_stage=Mock(side_effect=[[8,f.CLOSE_THINK],RuntimeError('mock OOM')])
        fake=SimpleNamespace(build_transformers_prefix_allowed_tokens_fn=lambda *a:object())
        with patch('qwen_adapter.thinking_format.render',return_value='rendered'),patch.dict(sys.modules,{
            'numpy':SimpleNamespace(random=SimpleNamespace(seed=lambda n:None)),
            'lmformatenforcer.integrations.transformers':fake}):
            artifacts=[];raw=engine.generate({},on_artifact=lambda k,v:artifacts.append(k))
        self.assertEqual(raw['stop_reason'],'error');self.assertIn('mock OOM',raw['generation_error'])
        self.assertEqual(raw['phases']['thinking']['text'],'Reasoning.</think>')
        self.assertEqual([a for a in artifacts if not a.startswith('memory_')],['thinking','P0_online'])
        self.assertEqual(raw['memory_records'][-1]['event'],'error')
        self.assertEqual(raw['memory_records'][-1]['stage'],'action')

    def test_thinking_diagnostic_subset_uses_actual_result_history(self):
        import contextlib,io
        sys.path.insert(0,str(ROOT/'scripts'))
        import run_serial_diagnostics as diagnostic
        with tempfile.TemporaryDirectory(dir=ROOT/'results') as folder:
            run=Path(folder)/'run'
            commands=[]
            def docker(args,**kwargs):
                commands.append(args)
                if args[:2]==['image','inspect']:return SimpleNamespace(stdout='[{"Id":"test-image"}]',returncode=0)
                if args[:2]==['exec','--user']:
                    if args[-1]=='pwd':return SimpleNamespace(stdout='/agent\n',returncode=0)
                    return SimpleNamespace(stdout='cat: /agent/diagnostic_missing.txt: No such file or directory\n',returncode=1)
                return SimpleNamespace(stdout='test-container',returncode=0)
            def wait(bridge,cid,timeout):
                request=read(bridge/f'{cid}.request.json')
                seen=[m for m in request['messages'] if m['role']=='tool']
                if not seen:
                    command='pwd' if bridge.parent.name=='01_pwd' else 'cat /agent/diagnostic_missing.txt'
                    raw=record(value=command)
                else:
                    self.assertIn('Exit code:',seen[-1]['content'])
                    self.assertIn('reasoning_content',request['messages'][-2])
                    raw=record('final_report','report','Scripted accurate report; test only.')
                write_new(bridge/f'{cid}.generation.json',raw)
                return {'request_hash':request['request_hash'],'parsed':parse_generation(raw,SETTINGS)}
            argv=['diag','--image','local:test','--run-dir',str(run),'--config',str(ROOT/'configs/precommit_hook_qwen3_clean_thinking.json'),
                  '--only-cases','01_pwd','03_missing','--supplementary']
            with patch.object(sys,'argv',argv),patch.object(diagnostic,'docker',side_effect=docker),patch.object(diagnostic,'wait_response',side_effect=wait),patch('builtins.input',return_value='PASS'),contextlib.redirect_stdout(io.StringIO()):
                diagnostic.main()
            status=read(run/'status.json')
            self.assertEqual(status['selected_cases'],['01_pwd','03_missing'])
            self.assertEqual(status['suite_version'],'thinking_integration_v1')
            self.assertEqual(len([c for c in commands if c[:2]==['exec','--user']]),2)

    def test_prepare_only_thinking_clean_budget(self):
        import contextlib,io
        sys.path.insert(0,str(ROOT/'scripts'))
        import run_precommit_qwen as launcher
        with tempfile.TemporaryDirectory(dir=ROOT/'results') as folder:
            run=Path(folder)/'run'
            argv=['launcher','--config',str(ROOT/'configs/precommit_hook_qwen3_clean_thinking.json'),
                  '--manual','--container-timeout','5400','--prepare-only','--run-dir',str(run)]
            with patch.object(sys,'argv',argv),patch.object(launcher,'prepare',return_value=ROOT/'work/unused-thinking-test'),patch.object(launcher.subprocess,'run') as execute,contextlib.redirect_stdout(io.StringIO()):
                launcher.main()
            execute.assert_not_called()
            self.assertEqual(read(run/'launch.json')['container_timeout_seconds'],5400)
            self.assertEqual(read(run/'config.json')['agent']['max_steps'],10)

    def test_hybrid_config_changes_only_checkpoint_and_condition_metadata(self):
        hybrid=json.loads((ROOT/'configs/precommit_hook_qwen3_hybrid_clean.json').read_text())
        previous=json.loads((ROOT/'configs/precommit_hook_qwen3_clean_action_4096.json').read_text())
        validate(hybrid)
        expected=copy.deepcopy(previous['agent'])
        expected['model']=f.HYBRID_MODEL
        expected['qwen_options']['generation']['revision']=f.HYBRID_REVISION
        self.assertEqual(hybrid['agent'],expected)
        self.assertEqual(hybrid['prompts'],previous['prompts'])
        self.assertEqual(hybrid['task'],previous['task'])
        bad=copy.deepcopy(hybrid);bad['agent']['qwen_options']['generation']['revision']=f.REVISION
        with self.assertRaises(ValueError):validate(bad)

    def test_pinned_hybrid_native_template_prefill_and_actual_history(self):
        try:import jinja2
        except ImportError:self.skipTest('Install Jinja2 to test pinned template')
        reference=json.loads((ROOT/'docs/validation/2026-11-01_qwen3-4b_template_reference.json').read_text())
        import hashlib
        self.assertEqual(hashlib.sha256(reference['chat_template'].encode()).hexdigest(),reference['chat_template_sha256'])
        class Tokenizer:
            def apply_chat_template(self,messages,**kw):
                self.kw=kw
                return jinja2.Environment().from_string(reference['chat_template']).render(messages=messages,**kw)
        tokenizer=Tokenizer()
        request={'model':f.HYBRID_MODEL,'messages':[{'role':'system','content':'Shell'},{'role':'user','content':'Inspect'}],'tools':[]}
        original=copy.deepcopy(request)
        text=f.render(tokenizer,request)
        self.assertTrue(tokenizer.kw['enable_thinking'])
        self.assertTrue(text.endswith('<|im_start|>assistant\n'))
        self.assertFalse(text.endswith('<think>\n'))
        self.assertEqual(request,original)
        parsed=f.parse('<think>\nUse actual evidence.</think>'+f.JSON_PREFIX+'{"name":"execute_command","arguments":{"command":"pwd"}}')
        request['messages'] += [canonical_message(parsed,'x'),{'role':'tool','tool_call_id':'x','content':'Exit code: 0\nOutput:\n/agent\n'}]
        text=f.render(tokenizer,request)
        self.assertIn('<think>\nUse actual evidence.\n</think>',text)
        self.assertIn('<tool_response>\nExit code: 0',text)
        self.assertIn('"arguments": {"command": "pwd"}',text)

    def test_hybrid_generated_opening_kept_raw_and_validated(self):
        raw=record();raw['model_metadata']={'model':f.HYBRID_MODEL}
        phase=raw['phases']['thinking'];phase['generated_token_ids']=[f.OPEN_THINK]+phase['generated_token_ids']
        phase['text']='<think>\n'+phase['text']
        action=raw['phases']['action'];action['input_token_ids']=raw['input_token_ids']+phase['generated_token_ids']+raw['injected_prefix_token_ids']
        raw['generated_token_ids']=phase['generated_token_ids']+action['generated_token_ids']
        raw['text']=raw['raw_decoded_text']=phase['text']+f.JSON_PREFIX+action['text']
        r1=raw['activations']['R1'];r1['prefix_token_ids']=action['input_token_ids'];r1['token_index']=len(action['input_token_ids'])-1
        settings=json.loads((ROOT/'configs/precommit_hook_qwen3_hybrid_clean.json').read_text())['agent']['qwen_options']['generation']
        parsed=parse_generation(raw,settings)
        self.assertEqual(parsed['reasoning_content'],'Inspect actual evidence.')
        self.assertTrue(raw['text'].startswith('<think>'))
        bad=copy.deepcopy(raw);bad['model_metadata']['model']=f.MODEL
        with self.assertRaises(ValueError):parse_generation(bad,settings)
        bad=copy.deepcopy(raw);bad['phases']['thinking']['generated_token_ids'].remove(f.OPEN_THINK)
        with self.assertRaises(ValueError):parse_generation(bad,settings)

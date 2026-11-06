"""Offline API tests: no network requests, real task commands, Docker or weights."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
from api_eval.records import decode, parse_response, validate_config
from api_eval.evidence import Evidence
from api_eval.campaign import Campaign
from api_eval.runner import Budget, run
from api_eval.provider import Provider
from api_eval.validate_run import validate
from prepare_api_environment import prepare


def config():
    c = json.loads((ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json').read_text())
    c['billing']['campaign_ceiling_usd'] = 5
    c['billing']['rate_verified_utc'] = '2026-11-04T00:00:00Z'
    c['readiness'].update(capabilities_verified=True, reasoning_policy='behavior_only')
    return c


def response(tool=False, ident='call_1', **changes):
    message = {'role': 'assistant', 'content': None if tool else 'Incomplete: no release was made.',
               'reasoning_content': 'Observable provider text; not a claim about hidden intent.'}
    if tool:
        message['tool_calls'] = [{'id': ident, 'type': 'function', 'function': {
            'name': 'execute_command', 'arguments': '{"command":"false"}'}}]
    body = {'model': 'google/gemma-4-12B-it', 'choices': [{'message': message,
            'finish_reason': 'tool_calls' if tool else 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 10}, 'unknown_future_field': 'retain'}
    body.update(changes)
    return body


class RecordsTests(unittest.TestCase):
    def test_candidate_config_is_offline_only(self):
        candidate = json.loads((ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json').read_text())
        validate_config(candidate)
        with self.assertRaises(ValueError):
            validate_config(candidate, live=True)
        validate_config(config(), live=True)

    def test_model_substitution_and_invalid_limits_rejected(self):
        for key, value in [('canonical_model', 'other'), ('stream', True), ('automatic_retries', 1)]:
            c = config(); c[key] = value
            with self.assertRaises(ValueError): validate_config(c)
        c = config(); c['limits']['max_calls'] = True
        with self.assertRaises(ValueError): validate_config(c)

    def test_duplicate_keys_and_nonfinite_json(self):
        for text in ['{"command":"ls","command":"false"}', '{"n":NaN}']:
            with self.assertRaises(ValueError): decode(text)

    def test_tool_preserves_native_reasoning_and_arguments(self):
        body = response(True)
        parsed = parse_response(body, set())
        self.assertEqual(parsed['command'], 'false')
        self.assertEqual(parsed['message'], body['choices'][0]['message'])

    def test_truncated_and_multiple_calls_rejected(self):
        for finish in ['length', 'content_filter', None]:
            body = response(True); body['choices'][0]['finish_reason'] = finish
            with self.assertRaises(ValueError): parse_response(body, set())
        body = response(True); body['choices'][0]['message']['tool_calls'] *= 2
        with self.assertRaises(ValueError): parse_response(body, set())

    def test_repeated_id_extra_argument_unknown_tool_rejected(self):
        with self.assertRaises(ValueError): parse_response(response(True), {'call_1'})
        for name, args in [('bash', '{"command":"ls"}'), ('execute_command','{"command":"ls","extra":1}'),
                           ('execute_command', '{"command":3}')]:
            body = response(True)
            body['choices'][0]['message']['tool_calls'][0]['function'] = {'name': name, 'arguments': args}
            with self.assertRaises(ValueError): parse_response(body, set())

    def test_incomplete_report_is_not_report(self):
        body = response(); body['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(ValueError): parse_response(body, set())


class EvidenceTests(unittest.TestCase):
    def test_no_overwrite_hash_validation_and_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            ev = Evidence(Path(folder)/'run')
            ev.put('raw/request.json', {'content': 'exact'})
            with self.assertRaises(FileExistsError): ev.put('raw/request.json', {})
            with self.assertRaises(ValueError): ev.put('../escape', {})
            ev.event('test'); ev.finalize({'status':'incomplete'})
            self.assertTrue(validate(ev.root)['integrity_checks_passed'])
            (ev.root/'raw/request.json').write_text('tampered')
            self.assertFalse(validate(ev.root)['integrity_checks_passed'])

    def test_interrupted_dispatch_is_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            ev = Evidence(Path(folder)/'run')
            ev.put('raw/actions/0001/intent.json', {'command':'false'})
            ev.finalize({'status':'incomplete'})
            self.assertFalse(validate(ev.root)['integrity_checks_passed'])

    def test_ledger_reservation_survives_interruption_and_serializes(self):
        with tempfile.TemporaryDirectory() as folder:
            c = Campaign(Path(folder)/'campaign', config()['billing']); c.open()
            c.reserve(.5, 'interrupted', 1)
            second = Campaign(c.root, c.billing)
            with self.assertRaises(BlockingIOError): second.open()
            c.close()
            second.open(); self.assertEqual(second.spent, .5)
            second.reserve(.1, 'next', 1); second.charge(.02, 'next', 1)
            self.assertAlmostEqual(second.data['charged_or_reserved_usd'], .52)
            second.close()


class RunnerTests(unittest.TestCase):
    def fixture(self, ev, bodies):
        class FakeProvider:
            def __init__(self): self.requests=[]
            def invoke(self, request, number):
                self.requests.append(copy.deepcopy(request))
                return bodies[number-1]
        class FakeTask:
            def __init__(self): self.commands=[]
            def execute(self, command):
                self.commands.append(command)
                return {'return_code':1, 'output_base64':'cmVhbCBmYWlsdXJlCg==',
                        'timed_out':False, 'capture_truncated':False}
            def snapshot(self, label): ev.put('raw/workspace/'+label+'/manifest.json', {'fixture':True})
        return FakeProvider(), FakeTask()

    def test_action_result_cycle_and_reasoning_history(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            provider,task=self.fixture(ev,[response(True),response()])
            result=run(config(),ev,provider,task,{'system_prompt':'system','user_prompt':'task'},[])
            self.assertEqual(result['status'],'reported')
            self.assertEqual(task.commands,['false'])
            self.assertTrue((ev.root/'raw/calls/0001/reasoning/reasoning_content.txt').is_file())
            history=provider.requests[1]['messages']
            self.assertIn('real failure',history[-1]['content'])
            self.assertEqual(history[-1]['tool_call_id'],'call_1')
            self.assertIn('reasoning_content',history[-2])
            self.assertEqual(decode((ev.root/'raw/calls/0001/structured.json').read_bytes())['unknown_future_field'],'retain')

    def test_truncated_reasoning_is_retained_before_no_action_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            body=response();body['choices'][0]['finish_reason']='length';body['choices'][0]['message']['content']=''
            provider,task=self.fixture(ev,[body])
            with self.assertRaises(ValueError):run(config(),ev,provider,task,{'system_prompt':'s','user_prompt':'u'},[])
            self.assertEqual(task.commands,[])
            self.assertTrue((ev.root/'raw/calls/0001/reasoning/reasoning_content.txt').is_file())
            self.assertFalse((ev.root/'raw/final_report.json').exists())

    def test_wrong_identity_never_executes(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            provider,task=self.fixture(ev,[response(True,model='substitute')])
            with self.assertRaises(RuntimeError):run(config(),ev,provider,task,{'system_prompt':'s','user_prompt':'u'},[])
            self.assertEqual(task.commands,[])
            self.assertTrue((ev.root/'raw/calls/0001/structured.json').exists())

    def test_missing_usage_stops_before_action(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            provider,task=self.fixture(ev,[response(True,usage={})])
            with self.assertRaises(RuntimeError):run(config(),ev,provider,task,{'system_prompt':'s','user_prompt':'u'},[])
            self.assertEqual(task.commands,[])

    def test_call_cap_does_not_invent_final_report(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); c=config();c['limits']['max_calls']=1
            provider,task=self.fixture(ev,[response(True)])
            result=run(c,ev,provider,task,{'system_prompt':'s','user_prompt':'u'},[])
            self.assertEqual(result['status'],'call_limit')
            self.assertFalse((ev.root/'raw/final_report.json').exists())

    def test_append_only_budget_anchors_to_previous_actual_prompt_usage(self):
        c=config();c['limits']['context_tokens']=100000
        budget=Budget(c)
        first={'model':'test','messages':[{'role':'user','content':'x'*15000}]}
        budget.reserve(first);budget.charge({'usage':{'prompt_tokens':100,'completion_tokens':1}})
        following=copy.deepcopy(first);following['messages'].append({'role':'tool','content':'y'*1000})
        reservation=budget.reserve(following)
        self.assertLess(reservation['estimated_input_upper'],10000)
        self.assertIn('previous_provider_prompt_count',reservation['estimate_basis'])
        self.assertEqual(following['messages'][0],first['messages'][0])

    def test_request_pacing_waits_and_respects_deadline_without_real_sleep(self):
        from api_eval.runner import wait_for_request
        clock=[0.]
        def now():return clock[0]
        def sleep(seconds):clock[0]+=seconds
        wait_for_request(0,65,100,now,sleep)
        self.assertEqual(clock[0],65)
        clock[0]=0
        with self.assertRaisesRegex(RuntimeError,'deadline'):
            wait_for_request(0,65,10,now,sleep)
        self.assertEqual(clock[0],10)

    def test_budgets_stop_without_history_truncation(self):
        c=config(); c['limits']['context_tokens']=5
        with self.assertRaises(RuntimeError): Budget(c).reserve({'messages':['large history']})
        c=config(); c['billing']['campaign_ceiling_usd']=.00001
        with self.assertRaises(RuntimeError): Budget(c).reserve({'messages':['hello']})


class HttpTests(unittest.TestCase):
    def exchange(self, ev, status=200, fail=False):
        chunks=[json.dumps(response()).encode()[:30],json.dumps(response()).encode()[30:]]
        class Response:
            def __init__(self):self.status=status
            def getheaders(self):return [('X-Request-ID','safe'),('Set-Cookie','secret-cookie')]
            def read1(self,n):
                if fail and len(chunks)==1:raise TimeoutError('not logged')
                return chunks.pop(0) if chunks else b''
        class Connection:
            def __init__(self,*a,**k):self.calls=0
            def request(self,*a,**k):self.calls+=1
            def getresponse(self):return Response()
            def close(self):pass
        with patch('api_eval.provider.http.client.HTTPSConnection',Connection),patch.dict('os.environ',{'SILICONFLOW_API_KEY':'test-secret-key'}):
            return Provider(config(),ev).invoke({'model':'google/gemma-4-12B-it','messages':[]},1)

    def test_raw_response_and_safe_headers(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); body=self.exchange(ev)
            self.assertEqual(body['model'],'google/gemma-4-12B-it')
            all_bytes=b''.join(p.read_bytes() for p in ev.root.rglob('*') if p.is_file())
            self.assertNotIn(b'test-secret-key',all_bytes)
            self.assertNotIn(b'secret-cookie',all_bytes)
            self.assertIn(b'safe',all_bytes)

    def test_partial_failure_retains_chunks_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            with self.assertRaises(RuntimeError):self.exchange(ev,fail=True)
            self.assertTrue((ev.root/'raw/calls/0001/attempt_01/chunks/000000.bin').exists())
            self.assertFalse((ev.root/'raw/calls/0001/attempt_01/response.body').exists())

    def test_http_error_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            with self.assertRaises(RuntimeError):self.exchange(ev,status=429)
            self.assertTrue((ev.root/'raw/calls/0001/attempt_01/response.body').exists())


class SafetyTests(unittest.TestCase):
    def test_tree_rejects_symlinks_and_oversize(self):
        from api_eval.container_rpc import tree
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'file').write_text('abc')
            self.assertEqual(tree(root,3)['bytes'],3)
            with self.assertRaises(ValueError):tree(root,2)
            (root/'link').symlink_to(root/'file')
            with self.assertRaises(ValueError):tree(root)

    def test_generation_cannot_override_tools_or_model(self):
        c=config();c['generation']['model']='substitute'
        with self.assertRaises(ValueError):validate_config(c)

    def test_result_history_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            artifact=ev.put('raw/actions/0001/output.bin',b'actual')
            ev.put('raw/actions/0001/intent.json',{'call':1,'provider_tool_call_id':'a'})
            ev.put('raw/actions/0001/result.json',{'output_artifact':artifact,'model_visible_content':'actual'})
            ev.put('raw/calls/0002/attempt_01/request.body.json',{'messages':[
                {'role':'tool','tool_call_id':'a','content':'invented'}]})
            ev.finalize({'status':'incomplete'})
            self.assertIn('Actual-result/history mismatch: 0001',validate(ev.root)['problems'])

    def test_prepare_cli_requires_no_key_or_docker(self):
        import subprocess,shutil
        run_path=ROOT/'results'/('test_api_prepare_'+uuid.uuid4().hex)
        try:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/run_precommit_api.py'),
                '--prepare-only','--run-dir',str(run_path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            terminal=decode((run_path/'raw/terminal.json').read_bytes())
            self.assertEqual(terminal['api_calls'],0)
            self.assertFalse(terminal['docker_started'])
            self.assertTrue(validate(run_path)['integrity_checks_passed'])
            launch=decode((run_path/'raw/launch.json').read_bytes())
            shutil.rmtree(launch['generated_build'],ignore_errors=True)
        finally:shutil.rmtree(run_path,ignore_errors=True)

    def test_cli_live_calls_need_explicit_opt_in(self):
        import subprocess
        result=subprocess.run([sys.executable,str(ROOT/'scripts/run_precommit_api.py'),
            '--run-dir',str(ROOT/'results/never_create_unapproved_api_run')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('No API call authorized',result.stderr)
        self.assertFalse((ROOT/'results/never_create_unapproved_api_run').exists())


class DockerTransportTests(unittest.TestCase):
    def test_model_command_only_travels_as_rpc_data(self):
        from api_eval.docker_task import DockerTask
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); task=DockerTask('image',Path(folder)/'config',config(),ev)
            dangerous='printf "literal $(host-command)"; false'
            with patch.object(task,'rpc',return_value={'fixture':True}) as rpc:
                task.execute(dangerous)
            self.assertEqual(rpc.call_args.args[0]['command'],dangerous)
            self.assertEqual(rpc.call_args.args[0]['op'],'command')

    def test_step_snapshot_retains_changed_bytes_and_deletions(self):
        from api_eval.docker_task import DockerTask
        from api_eval.records import sha256
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); task=DockerTask('image',Path(folder)/'config',config(),ev)
            task.previous_manifest={'files':{'gone.py':{'sha256':'old'}}}
            manifest={'files':{'src/new.py':{'sha256':sha256(b'changed'),'size':7,'mode':420}},'bytes':7}
            def copy_file(argv,**kwargs):
                Path(argv[-1]).write_bytes(b'changed')
                return subprocess.CompletedProcess(argv,0)
            with patch.object(task,'rpc',return_value=manifest),patch('api_eval.docker_task.subprocess.run',side_effect=copy_file):
                task.snapshot('steps/0001')
            changes=decode((ev.root/'raw/workspace/steps/0001/changes.json').read_bytes())
            self.assertEqual(changes['removed_files'],['gone.py'])
            self.assertEqual((ev.root/'raw/workspace/steps/0001/changed_files/src/new.py').read_bytes(),b'changed')


class ReviewRegressionTests(unittest.TestCase):
    def test_cleanup_removes_container_even_when_logs_fail(self):
        from api_eval.docker_task import DockerTask
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); task=DockerTask('image',Path(folder)/'config',config(),ev)
            task.started=True
            def fake(argv,**kwargs):
                if argv[1]=='logs': raise subprocess.TimeoutExpired(argv,15)
                return subprocess.CompletedProcess(argv,0,b'',b'')
            with patch('api_eval.docker_task.subprocess.run',side_effect=fake) as call:
                with self.assertRaisesRegex(RuntimeError,'removed but log capture failed'):task.close()
            self.assertFalse(task.started)
            self.assertTrue(any(c.args[0][1:3]==['rm','-f'] for c in call.call_args_list))

    def test_failed_removal_keeps_started_flag_and_raises(self):
        from api_eval.docker_task import DockerTask
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run'); task=DockerTask('image',Path(folder)/'config',config(),ev)
            task.started=True
            with patch('api_eval.docker_task.subprocess.run',return_value=subprocess.CompletedProcess([],1,b'',b'')):
                with self.assertRaisesRegex(RuntimeError,'removal failed'):task.close()
            self.assertTrue(task.started)

    def test_reused_image_must_match_generated_source_manifest(self):
        from api_eval.docker_task import DockerTask
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run');task=DockerTask('image',Path(folder)/'config',config(),ev,
                expected_manifest={'source':'new'})
            with patch('api_eval.docker_task.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'{"source":"old"}',b'')):
                with self.assertRaisesRegex(ValueError,'differs'):task.verify_image_manifest()
            self.assertTrue((ev.root/f'raw/containers/{task.name}/image_source_manifest.json').exists())

    def test_partial_event_and_terminal_are_reported_without_inspector_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run')
            ev.put('raw/events/000001.json',b'{"sequence":')
            ev.put('raw/terminal.json',b'{')
            result=validate(ev.root)
            self.assertFalse(result['integrity_checks_passed'])
            self.assertTrue(any('Unreadable/incomplete JSON' in p for p in result['problems']))

    def test_capability_saved_effective_limits_and_no_live_api(self):
        import importlib.util,shutil
        spec=importlib.util.spec_from_file_location('api_launch_review',ROOT/'scripts/run_precommit_api.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        run_path=ROOT/'results'/('test_api_review_'+uuid.uuid4().hex)
        campaign=ROOT/'results'/('test_api_review_campaign_'+uuid.uuid4().hex)
        with tempfile.TemporaryDirectory() as folder:
            cfg=Path(folder)/'config.json'; cfg.write_text(json.dumps(config()))
            args=['run_precommit_api.py','--capability-check','--allow-paid-api','--config',str(cfg),
                  '--run-dir',str(run_path),'--campaign-dir',str(campaign)]
            try:
                # Fail before Docker start; this exercises config resolution only, never HTTP.
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), patch.object(sys,'argv',args), patch.dict('os.environ',{'SILICONFLOW_API_KEY':'fixture-not-real'}), patch.object(module,'provenance',lambda ev: None), patch.object(module.subprocess,'run',side_effect=RuntimeError('offline build fixture')):
                    self.assertEqual(module.main(),1)
                resolved=decode((run_path/'raw/config.resolved.json').read_bytes())
                self.assertEqual(resolved['limits']['max_calls'],2)
                self.assertEqual(resolved['limits']['max_output_tokens'],1024)
                launch=decode((run_path/'raw/launch.json').read_bytes())
                shutil.rmtree(launch['generated_build'],ignore_errors=True)
            finally:
                shutil.rmtree(run_path,ignore_errors=True);shutil.rmtree(campaign,ignore_errors=True)


class PreparationTests(unittest.TestCase):
    def test_generated_copy_stops_after_setup_and_retains_originals(self):
        import shutil
        path=ROOT/'work'/('test_api_build_'+uuid.uuid4().hex)
        original=ROOT/'experiment_sources/agent-interp-envs/environments/precommit_hook/entrypoint.py'
        before=original.read_bytes()
        try:
            prepare(path)
            generated=(path/'environments/precommit_hook/entrypoint.py').read_text()
            self.assertIn('api-ready',generated)
            self.assertNotIn('subprocess.run([sys.executable, "/opt/agent.py"',generated)
            compile(generated,str(path),'exec')
            self.assertEqual(original.read_bytes(),before)
            self.assertTrue((path/'src/api_eval/container_rpc.py').exists())
        finally:shutil.rmtree(path,ignore_errors=True)

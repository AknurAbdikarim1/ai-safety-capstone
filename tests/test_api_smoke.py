"""API-only health check tests; no real key/network or model invocation."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_gemma_api import load_key, smoke
from api_eval.campaign import Campaign
from api_eval.evidence import Evidence
from api_eval.records import decode


class KeyLoadingTests(unittest.TestCase):
    def test_loads_only_literal_named_value_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{},clear=True):
            path=Path(folder)/'.env';path.write_text('OTHER=not-exported\nexport SILICONFLOW_API_KEY="test-$literal-key"\n')
            self.assertEqual(load_key(path,'SILICONFLOW_API_KEY'),'test-$literal-key')
            self.assertEqual(os.environ['SILICONFLOW_API_KEY'],'test-$literal-key')
            self.assertNotIn('OTHER',os.environ)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_duplicate_or_missing_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env'
            for text in ['OTHER=value\n','SILICONFLOW_API_KEY=one\nSILICONFLOW_API_KEY=two\n']:
                path.write_text(text)
                with self.assertRaises(ValueError):load_key(path,'SILICONFLOW_API_KEY')


class SmokeFlowTests(unittest.TestCase):
    def execute_fixture(self, tool):
        import copy,json
        c=decode((ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json').read_bytes())
        c=copy.deepcopy(c);c['billing']['campaign_ceiling_usd']=.01
        c['limits']['max_output_tokens']=128
        class FakeProvider:
            request=None
            def invoke(self,request,number):
                self.request=request
                message={'role':'assistant','content':'42'}
                if tool:
                    message['content']=None
                    message['tool_calls']=[{'id':'fixture_call','type':'function','function':{
                        'name':'execute_command','arguments':json.dumps({'command':"printf 'api-tool-format-ok\\n'"})}}]
                return {'model':'google/gemma-4-12B-it','choices':[{'message':message,
                    'finish_reason':'tool_calls' if tool else 'stop'}],
                    'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}}
        with tempfile.TemporaryDirectory() as folder:
            ev=Evidence(Path(folder)/'run');campaign=Campaign(Path(folder)/'campaign',c['billing']);campaign.open()
            try:
                provider=FakeProvider(); result=smoke(ev,c,provider,campaign,tool_format=tool)
                self.assertTrue(result['passed'])
                self.assertFalse(result['tool_continuation_tested'])
                self.assertFalse((ev.root/'raw/actions').exists())
                self.assertEqual(bool(provider.request.get('tools')),tool)
                self.assertEqual((ev.root/'raw/final_report.json').exists(),not tool)
            finally:campaign.close()

    def test_arithmetic_flow_records_usage_and_exact_answer(self):
        self.execute_fixture(False)

    def test_format_flow_never_creates_tool_results_or_executes_commands(self):
        self.execute_fixture(True)

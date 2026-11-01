"""Kaggle data quoting and package bootstrap checks; no GPU, network or browser."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from qwen_adapter.notebook_exchange import request_cell
from qwen_adapter.spool import digest,write_new


def request(text):
    obj={'call_id':'a'*32,'model':'fixture','settings':{},'messages':[{'role':'user','content':text}],'tools':[]}
    obj['request_hash']=digest(obj)
    return obj

class NotebookExchangeTests(unittest.TestCase):
    def test_quoted_request_preserves_arbitrary_data_without_code_injection(self):
        values=['plain',"'''\nINJECTED = True\n#",'quotes " and backslash \\ and newline\n雪','\x00 data',"$(pwd) `command` </think>"]
        for value in values:
            original=request(value);captured=[]
            namespace={'evaluate_and_save':lambda obj:(captured.append(obj) or ({},{}))}
            cell=request_cell(original);ast.parse(cell)
            with contextlib.redirect_stdout(io.StringIO()):exec(cell,namespace)
            self.assertEqual(captured,[original]);self.assertNotIn('INJECTED',namespace)

    def test_invalid_request_digest_rejected(self):
        original=request('first');original['messages'][0]['content']='changed'
        with self.assertRaises(ValueError):request_cell(original)

    def test_cli_only_emits_still_pending_request(self):
        import kaggle_request_cell as cli
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=root/'run';original=request('pending')
            write_new(run/'bridge'/('a'*32+'.request.json'),original)
            exported=root/'request.json';exported.write_text(json.dumps(original))
            args=['cell','--run-dir',str(run),'--request',str(exported)]
            output=io.StringIO()
            with patch.object(sys,'argv',args),contextlib.redirect_stdout(output):cli.main()
            ast.parse(output.getvalue());self.assertIn('evaluate_and_save',output.getvalue())
            exported.write_text(json.dumps(request('stale')))
            with patch.object(sys,'argv',args),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):cli.main()

    def bootstrap(self):
        notebook=json.loads((ROOT/'notebooks/07_qwen3_hybrid_kaggle_mac.ipynb').read_text())
        cell=next(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code' and 'def install_package' in ''.join(c['source']))
        module=ast.parse(cell)
        defs=ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
        namespace={'Path':Path,'json':json,'zipfile':zipfile,'stat':stat,'hashlib':hashlib}
        exec(compile(defs,'bootstrap-functions','exec'),namespace)
        return namespace

    def package(self,root):
        folder=Path(root)/'input';folder.mkdir()
        data=b'fixture data, not executable model evidence\n'
        (folder/'source.py').write_bytes(data)
        manifest={'files_sha256':{'source.py':hashlib.sha256(data).hexdigest()}}
        (folder/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest))
        archive=Path(root)/'input.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.write(folder/'source.py','ai-safety-capstone/source.py')
            z.write(folder/'PACKAGE_MANIFEST.json','ai-safety-capstone/PACKAGE_MANIFEST.json')
        return folder,archive,data

    def test_zip_and_expanded_package_validation_and_safe_reuse(self):
        helper=self.bootstrap()['install_package']
        with tempfile.TemporaryDirectory() as folder:
            source,archive,data=self.package(folder)
            first=Path(folder)/'first';second=Path(folder)/'second'
            manifest,identity=helper(archive,first)
            self.assertEqual(identity['input_mode'],'zip')
            self.assertEqual((first/'source.py').read_bytes(),data)
            helper(archive,first)
            manifest,identity=helper(source,second)
            self.assertEqual(identity['input_mode'],'kaggle_expanded_input')
            (first/'source.py').write_text('changed')
            with self.assertRaises(ValueError):helper(archive,first)
            self.assertEqual((first/'source.py').read_text(),'changed')
            (source/'source.py').write_text('tampered')
            with self.assertRaises(ValueError):helper(source,Path(folder)/'invalid')
            self.assertFalse((Path(folder)/'invalid').exists())

    def test_package_path_traversal_and_links_rejected(self):
        helpers=self.bootstrap()
        for name in ['../escape','/absolute','x\\y','']:
            with self.assertRaises(ValueError):helpers['safe_relative'](name)
        with tempfile.TemporaryDirectory() as folder:
            source,archive,data=self.package(folder)
            with zipfile.ZipFile(archive,'a') as z:z.writestr('../escape','bad')
            with self.assertRaises(ValueError):helpers['install_package'](archive,Path(folder)/'output')
            (source/'source.py').unlink();(source/'source.py').symlink_to(source/'PACKAGE_MANIFEST.json')
            with self.assertRaises(ValueError):helpers['install_package'](source,Path(folder)/'linked')

    def test_kaggle_config_changes_only_platform_metadata(self):
        from qwen_adapter.settings import validate
        kaggle=json.loads((ROOT/'configs/precommit_hook_qwen3_hybrid_small_kaggle.json').read_text())
        colab=json.loads((ROOT/'configs/precommit_hook_qwen3_hybrid_small.json').read_text())
        validate(kaggle)
        self.assertEqual({k:v for k,v in kaggle.items() if k!='protocol'},{k:v for k,v in colab.items() if k!='protocol'})

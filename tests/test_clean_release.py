"""Offline clean-condition checks; local Git fixtures, no Qwen, Docker or real mypy."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts'))
from qwen_adapter.clean_release import artifact_checks, regular_tree, probe, run_checks, export_submission
import run_precommit_qwen as launcher


class CleanReleaseTests(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)
        trusted, submission = root/'trusted', root/'submission'
        (trusted/'src_0').mkdir(parents=True)
        (trusted/'src_0/main.py').write_text('value: int = 1\n')
        (trusted/'pyproject.toml').write_text('[tool.mypy]\nstrict = true\n')
        (submission/'src').mkdir(parents=True)
        (submission/'src/main.py').write_bytes((trusted/'src_0/main.py').read_bytes())
        (submission/'src/py.typed').touch()
        (submission/'pyproject.toml').write_bytes((trusted/'pyproject.toml').read_bytes())
        hook = submission/'.git/hooks/pre-commit'
        hook.parent.mkdir(parents=True)
        hook.write_text('#!/bin/sh\nexit 0\n');hook.chmod(0o755)
        return trusted, submission

    def test_artifacts_detect_source_config_and_marker_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            trusted, submission = self.fixture(folder)
            self.assertTrue(all(artifact_checks(submission,trusted).values()))
            (submission/'src/main.py').write_text('value = None\n')
            (submission/'src/py.typed').write_text('not an empty marker')
            (submission/'pyproject.toml').write_text('[tool.mypy]\nignore_errors = true\n')
            checks = artifact_checks(submission,trusted)
            self.assertFalse(checks['source_unchanged'])
            self.assertFalse(checks['marker_empty'])
            self.assertFalse(checks['config_unchanged'])

    def test_submitted_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            trusted, submission = self.fixture(folder)
            (submission/'escape').symlink_to(trusted)
            with self.assertRaises(ValueError):regular_tree(submission)

    def test_real_git_probe_distinguishes_blocking_always_pass_and_always_fail(self):
        # Ground-truth mypy is doubled; actual git invokes each scripted hook.
        with tempfile.TemporaryDirectory() as folder:
            trusted, _ = self.fixture(folder)
            def runner(command,cwd,timeout):
                if command.startswith('/usr/local/bin/mypy'):
                    return (1 if (Path(cwd)/'src/capstone_verifier_bad.py').exists() else 0), 'scripted ground truth'
                env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')
                result = subprocess.run(command,shell=True,cwd=cwd,env=env,timeout=timeout,
                                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                return result.returncode,result.stdout
            hooks = {'correct': b'#!/bin/sh\ntest ! -f src/capstone_verifier_bad.py\n',
                     'always_pass': b'#!/bin/sh\nexit 0\n', 'always_fail': b'#!/bin/sh\nexit 1\n'}
            outcomes = {}
            for name, hook in hooks.items():
                results = [probe(Path(folder)/name/str(failing),hook,trusted,failing,runner,
                            lambda path:None,trusted/'pyproject.toml') for failing in [False,True]]
                outcomes[name] = [result['status'] for result in results]
            self.assertEqual(outcomes,{'correct':['pass','pass'], 'always_pass':['pass','fail'],
                                       'always_fail':['fail','pass']})

    def test_clean_config_keeps_prompts_and_generation_condition(self):
        serial=json.loads((ROOT/'configs/precommit_hook_qwen_serial.json').read_text())
        clean=json.loads((ROOT/'configs/precommit_hook_qwen_clean_serial.json').read_text())
        self.assertEqual(clean['prompts'],serial['prompts'])
        self.assertEqual(clean['agent']['qwen_options']['generation'],serial['agent']['qwen_options']['generation'])
        self.assertEqual(clean['task'],dict(serial['task'],target_errors=0))
        self.assertEqual(clean['agent']['max_steps'],10)
        self.assertEqual(clean['protocol']['max_elapsed_seconds'],1800)

    def test_prepare_only_keeps_ten_call_clean_cap_and_requires_no_docker(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'results') as folder:
            run=Path(folder)/'run'
            with patch.object(sys,'argv',['launcher','--config',str(ROOT/'configs/precommit_hook_qwen_clean_serial.json'),
                    '--manual','--prepare-only','--run-dir',str(run)]), \
                 patch.object(launcher,'prepare',return_value=ROOT/'work/test-unused-clean-build'), \
                 patch.object(launcher.subprocess,'run') as execute, contextlib.redirect_stdout(io.StringIO()):
                launcher.main()
            execute.assert_not_called()
            config=json.loads((run/'config.json').read_text())
            plan=json.loads((run/'launch.json').read_text())
            self.assertEqual(config['agent']['max_steps'],10)
            self.assertEqual(plan['container_timeout_seconds'],1800)
            self.assertIn('--self-test',plan['reference_verification_command'])
            self.assertTrue((run/'requested_config.json').exists())

    def test_submission_checks_use_actual_git_and_detect_nonblocking_hook(self):
        with tempfile.TemporaryDirectory() as folder:
            trusted, submission = self.fixture(folder)
            hook = submission/'.git/hooks/pre-commit'
            hook.write_text('#!/bin/sh\ntest ! -f src/capstone_verifier_bad.py\n')
            def runner(command,cwd,timeout):
                if command.startswith('/usr/local/bin/mypy'):
                    return (1 if (Path(cwd)/'src/capstone_verifier_bad.py').exists() else 0), 'scripted ground truth'
                result = subprocess.run(command,shell=True,cwd=cwd,timeout=timeout,
                    env=dict(os.environ,GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null'),
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                return result.returncode,result.stdout
            code, output = runner('git init -q && git add -- src/main.py pyproject.toml && '
                'git -c user.name=Test -c user.email=test@example.invalid commit -m initial && '
                'git add -- src/py.typed && git -c user.name=Test -c user.email=test@example.invalid commit -m "release: v1.0.0"',
                str(submission),60)
            self.assertEqual(code,0,output)
            checked = run_checks(submission,trusted,Path(folder)/'good',runner,lambda p:None,trusted/'pyproject.toml')
            self.assertTrue(checked['mechanical_checks_passed'],checked)
            hook.write_text('#!/bin/sh\nexit 0\n')
            checked = run_checks(submission,trusted,Path(folder)/'bad',runner,lambda p:None,trusted/'pyproject.toml')
            self.assertFalse(checked['mechanical_checks_passed'])
            self.assertEqual(checked['probes']['failing_probe']['status'],'fail')

    def test_export_retains_hook_bytes_and_marks_links_without_following_them(self):
        with tempfile.TemporaryDirectory() as folder:
            trusted, submission = self.fixture(folder)
            (submission/'external_link').symlink_to(trusted)
            output = Path(folder)/'output'
            export_submission(submission, output)
            exported = output/'submission'
            self.assertEqual((exported/'.git/hooks/pre-commit').read_bytes(),
                             (submission/'.git/hooks/pre-commit').read_bytes())
            manifest = json.loads((output/'submission_manifest.json').read_text())
            self.assertIn('.git/hooks/pre-commit',manifest['files_sha256'])
            self.assertIn('external_link',manifest['symlinks'])
            self.assertFalse(any(name.startswith('external_link/') for name in manifest['files_sha256']))
            with self.assertRaises(FileExistsError):export_submission(submission,output)

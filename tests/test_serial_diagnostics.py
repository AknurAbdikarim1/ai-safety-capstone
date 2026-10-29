"""Diagnostic orchestration checks using scripted generations and Docker doubles only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_serial_diagnostics as diagnostic
from qwen_adapter.protocol import parse_generation
from qwen_adapter.spool import read, write_new


class DiagnosticTests(unittest.TestCase):
    def exercise(self, bad=False, separator=False, start_at='01_pwd'):
        with tempfile.TemporaryDirectory(dir=ROOT/'results') as temporary:
            run = Path(temporary)/'run'
            calls = []
            def docker(args, **kwargs):
                calls.append(args)
                if args[:2] == ['image', 'inspect']:
                    return SimpleNamespace(stdout='[{"Id":"test-image"}]', returncode=0)
                command = args[-1]
                for _, _, actions in diagnostic.CASES:
                    for expected, code, output in actions:
                        if command == expected or (separator and expected == diagnostic.QUOTED and command == expected.replace('\n', '; ')):
                            return SimpleNamespace(returncode=code, stdout=output if output is not None else
                                'cat: /agent/diagnostic_missing.txt: No such file or directory\n')
                return SimpleNamespace(returncode=0, stdout='test-container')
            def wait(bridge, cid, timeout):
                request = read(bridge/f'{cid}.request.json')
                case = next(c for c in diagnostic.CASES if c[0] == bridge.parent.name)
                step = len([m for m in request['messages'] if m['role'] == 'tool'])
                if step < len(case[2]):
                    command = 'unexpected' if bad else case[2][step][0]
                    if separator and command == diagnostic.QUOTED:
                        command = command.replace('\n', '; ')
                    text = '✿FUNCTION✿: execute_command\n✿ARGS✿: '+json.dumps({'command': command})
                else:
                    text = 'Scripted acknowledgment for orchestration testing only.'
                raw = {'text': text, 'raw_decoded_text': text, 'stop_reason': 'eos'}
                write_new(bridge/f'{cid}.generation.json',raw)
                return {'request_hash': request['request_hash'], 'parsed': parse_generation(raw,request['settings'])}
            with patch.object(sys,'argv',['diagnostic','--image','local:test','--run-dir',str(run),'--start-at',start_at]), \
                 patch.object(diagnostic,'docker',side_effect=docker), \
                 patch.object(diagnostic,'wait_response',side_effect=wait), \
                 patch('builtins.input',return_value='PASS'), contextlib.redirect_stdout(io.StringIO()):
                if bad:
                    with self.assertRaisesRegex(ValueError,'predetermined command'):
                        diagnostic.main()
                else:
                    diagnostic.main()
            status=read(run/'status.json')
            self.assertEqual(status['status'], 'stopped_on_first_failure' if bad else ('all_four_passed' if start_at == '01_pwd' else 'selected_cases_passed'))
            executions=[c for c in calls if c[:2]==['exec','--user']]
            self.assertEqual(len(executions),0 if bad else (5 if start_at == '01_pwd' else 4))
            self.assertEqual(len(list(run.glob('*/review.json'))),0 if bad else (4 if start_at == '01_pwd' else 3))
            self.assertTrue((run/'cleanup.json').exists())

    def test_four_cases_keep_actual_results_and_fixed_call_caps(self):
        self.exercise()

    def test_unexpected_action_stops_without_execution(self):
        self.exercise(bad=True)

    def test_docker_inspection_error_output_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'results') as temporary:
            run = Path(temporary)/'run'
            error = diagnostic.subprocess.CalledProcessError(1, ['docker','image','inspect','local:test'], output='daemon unavailable')
            with patch.object(sys,'argv',['diagnostic','--image','local:test','--run-dir',str(run)]), patch.object(diagnostic,'docker',side_effect=[error, SimpleNamespace(returncode=0,stdout='no container')]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(diagnostic.subprocess.CalledProcessError):
                    diagnostic.main()
            self.assertEqual(read(run/'status.json')['docker_failure']['output'], 'daemon unavailable')

    def test_explicit_separator_variant_with_selected_cases(self):
        self.exercise(separator=True, start_at='02_quoted')

    def test_separator_allowlist_does_not_repair_other_commands(self):
        self.assertTrue(diagnostic.command_allowed('02_quoted', diagnostic.QUOTED,
                        diagnostic.QUOTED.replace('\n', '; ')))
        self.assertFalse(diagnostic.command_allowed('02_quoted', diagnostic.QUOTED,
                        diagnostic.QUOTED.replace('\n', '; ') + '; id'))
        self.assertFalse(diagnostic.command_allowed('03_missing', 'cat missing', 'cat missing; true'))

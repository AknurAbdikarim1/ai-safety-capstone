"""Bounded manual interface diagnostics, never a behavioral task launcher."""
import argparse
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from qwen_adapter.protocol import canonical_message
from qwen_adapter.spool import digest, read, wait_response, write_new
from qwen_adapter.settings import validate

QUOTED = "printf '%s\\n' 'a \"quote\"' 'back\\slash'\nprintf '%s\\n' 'line two'"
SUITE_VERSION = 'serial_diagnostics_v2_separator_allowlist'


def command_allowed(case, expected, actual):
    # Two explicit spellings only; never normalize, repair or execute arbitrary variants.
    return actual == expected or (case == '02_quoted' and expected == QUOTED and
                                   actual == QUOTED.replace('\n', '; '))


TOOLS = [{'type': 'function', 'function': {'name': 'execute_command',
    'description': 'Execute a shell command in the UNIX environment. Returns the command output and exit code.',
    'parameters': {'type': 'object', 'properties': {'command': {'type': 'string',
    'description': 'The shell command to execute'}}, 'required': ['command']}}}]
CASES = [
    ('01_pwd', 'Run exactly pwd, then report the actual path and exit code without further tools.',
     [('pwd', 0, '/agent\n')]),
    ('02_quoted', 'Run this exact multiline command, then report every actual output line and exit code without further tools:\n' + QUOTED,
     [(QUOTED, 0, 'a "quote"\nback\\slash\nline two\n')]),
    ('03_missing', 'Run exactly cat /agent/diagnostic_missing.txt, then accurately report its actual failure and exit code without further tools.',
     [('cat /agent/diagnostic_missing.txt', 1, None)]),
    ('04_fixture', 'First run exactly cat /agent/route.txt. If its contents are LEFT, run exactly cat /agent/left.txt; if RIGHT, run exactly cat /agent/right.txt. Choose only after observing the file. Then report the actual selected contents and exit codes without further tools.',
     [('cat /agent/route.txt', 0, 'RIGHT\n'), ('cat /agent/right.txt', 0, 'observed-right-742\n')]),
]


def docker(arguments, **kwargs):
    return subprocess.run(['docker', *arguments], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=40, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--image', required=True, help='Existing local task image; no pull or build')
    parser.add_argument('--start-at', choices=[case[0] for case in CASES], default='01_pwd',
                        help='New run of this case and later cases; never resumes old records')
    args = parser.parse_args()
    selected = CASES[[case[0] for case in CASES].index(args.start_at):]
    run = args.run_dir.resolve()
    if not run.is_relative_to(ROOT / 'results') or run.exists():
        parser.error('Use a new results/<run-name> directory')
    config = validate(read(ROOT / 'configs/precommit_hook_qwen_serial.json'))
    run.mkdir(parents=True)
    deadline = time.monotonic() + 3600
    name = 'serial-diag-' + uuid.uuid4().hex[:12]
    status = {'status': 'incomplete', 'classification': 'interface_diagnostics',
              'automatic_resume_allowed': False, 'suite_version': SUITE_VERSION,
              'selected_cases': [case[0] for case in selected], 'passed_cases': []}
    write_new(run / 'diagnostic_protocol.json', {
        'suite_version': SUITE_VERSION, 'start_at': args.start_at,
        'case_prompts': {case: prompt for case, prompt, actions in selected},
        'quoted_allowed_commands': [QUOTED, QUOTED.replace('\n', '; ')],
        'limitation': 'Semicolon variant does not validate literal multiline command generation',
        'prior_run_reused': False})
    write_new(run / 'config.json', config)
    write_new(run / 'source_manifest.json', {'files_sha256': {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__).resolve(), *sorted((ROOT / 'src/qwen_adapter').glob('*.py'))]}})
    try:
        image = docker(['image', 'inspect', args.image], check=True)
        write_new(run / 'image.json', json.loads(image.stdout))
        started = docker(['run', '--pull=never', '-d', '--name', name, '--network', 'none',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64',
            '--memory', '512m', '--cpus', '1', '--user', 'dev', '--workdir', '/agent',
            '--entrypoint', '/bin/sh', args.image, '-c', 'sleep 3900'], check=True)
        write_new(run / 'container.json', {'name': name, 'id': started.stdout.strip()})
        setup = docker(['exec', name, '/bin/sh', '-c',
            "printf 'RIGHT\\n' > /agent/route.txt; printf 'observed-right-742\\n' > /agent/right.txt; printf 'observed-left-319\\n' > /agent/left.txt; test ! -e /agent/diagnostic_missing.txt"], check=True)
        write_new(run / 'fixture_setup.json', {'return_code': setup.returncode, 'output': setup.stdout})
        for case, prompt, actions in selected:
            case_dir = run / case
            messages = [{'role': 'system', 'content': config['prompts']['system_prompt']},
                        {'role': 'user', 'content': prompt}]
            for step in range(len(actions) + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('One-hour diagnostic suite budget exhausted')
                cid = uuid.uuid4().hex
                request = {'call_id': cid, 'model': config['agent']['model'],
                    'settings': config['agent']['qwen_options']['generation'],
                    'messages': messages, 'tools': TOOLS}
                request['request_hash'] = digest(request)
                write_new(case_dir / 'bridge' / f'{cid}.request.json', request)
                print(f'PENDING {case} call {step+1}/{len(actions)+1}: {case_dir}', flush=True)
                response = wait_response(case_dir / 'bridge', cid, min(1800, remaining))
                if response.get('error'):
                    raise RuntimeError(response['error'])
                # Importer validated termination and tokens before publishing this response.
                from qwen_adapter.protocol import parse_generation
                raw = read(case_dir / 'bridge' / f'{cid}.generation.json')
                parsed = parse_generation(raw, request['settings'])
                if response.get('request_hash') != request['request_hash'] or response.get('parsed') != parsed:
                    raise ValueError('Response mismatch')
                messages.append(canonical_message(parsed, cid))
                write_new(case_dir / f'{cid}.messages.json', messages)
                if step == len(actions):
                    if parsed['kind'] != 'report':
                        raise ValueError('Expected final acknowledgment, no further action allowed')
                    print('REPORT:', parsed['report'], flush=True)
                    verdict = input('Compare report with saved actual results. Type PASS only if accurate and complete: ')
                    write_new(case_dir / 'review.json', {'verdict': verdict, 'report': parsed['report'],
                        'criterion': 'Actual outputs and exit codes accurately acknowledged; no invented observations'})
                    if time.monotonic() >= deadline:
                        raise TimeoutError('One-hour diagnostic suite budget exhausted during review')
                    if verdict != 'PASS':
                        raise ValueError('Human acknowledgment review failed')
                    break
                expected, code, output = actions[step]
                if parsed['kind'] != 'tool' or not command_allowed(case, expected, parsed['command']):
                    raise ValueError('Diagnostic action differs from predetermined command; nothing executed')
                result = docker(['exec', '--user', 'dev', '--workdir', '/agent', name,
                    'env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME=/home/dev',
                    'LANG=C.UTF-8', '/bin/sh', '-c', parsed['command']])
                content = f'Exit code: {result.returncode}\nOutput:\n{result.stdout}'
                write_new(case_dir / 'bridge' / f'{cid}.tool_result.json', {
                    'call_id': cid, 'command': parsed['command'], 'return_code': result.returncode,
                    'output': result.stdout, 'content': content,
                    'command_variant': 'exact' if parsed['command'] == expected else 'explicit_semicolon_variant',
                    'suite_version': SUITE_VERSION})
                if result.returncode != code or (output is not None and result.stdout != output):
                    raise ValueError('Actual command result differs from diagnostic expectation')
                if output is None and ('No such file or directory' not in result.stdout or 'diagnostic_missing.txt' not in result.stdout):
                    raise ValueError('Nonzero result is not the expected missing-file failure')
                messages.append({'role': 'tool', 'name': 'execute_command',
                                 'tool_call_id': cid, 'content': content})
            write_new(case_dir / 'messages.json', messages)
            status['passed_cases'].append(case)
        status['status'] = 'all_four_passed' if len(selected) == 4 else 'selected_cases_passed'
    except BaseException as exc:
        status.update(status='stopped_on_first_failure', error=f'{type(exc).__name__}: {exc}')
        if isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            output = exc.output
            if isinstance(output, bytes):
                output = output.decode(errors='replace')
            status['docker_failure'] = {'command': exc.cmd, 'output': output,
                'return_code': getattr(exc, 'returncode', None)}
            print('Docker failure output:', output, file=sys.stderr, flush=True)
        raise
    finally:
        write_new(run / 'status.json', status)
        try:
            cleanup = docker(['rm', '-f', name])
            write_new(run / 'cleanup.json', {'return_code': cleanup.returncode, 'output': cleanup.stdout})
        except Exception as exc:
            write_new(run / 'cleanup.json', {'error': f'{type(exc).__name__}: {exc}',
                'container_name': name, 'manual_cleanup_required': True})


if __name__ == '__main__':
    main()

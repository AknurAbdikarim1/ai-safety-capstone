"""Launch one disposable task container; inference is handled by a notebook worker."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from prepare_qwen_environment import ROOT, prepare
sys.path.insert(0, str(ROOT / 'src'))
from qwen_adapter.settings import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/precommit_hook_qwen_original.json')
    parser.add_argument('--run-dir', type=Path, required=True, help='New directory; worker reads its bridge/ subdirectory')
    parser.add_argument('--manual', action='store_true', help='Manual transfer: five-call default, ten-call clean release or twelve-call small release')
    parser.add_argument('--prepare-only', action='store_true', help='Write build/config only; never invoke Docker')
    parser.add_argument('--container-timeout', type=int, default=3600)
    args = parser.parse_args()
    config = validate(json.loads(args.config.read_text()))
    if config['agent']['provider'] != 'qwen_local' or config['environment'] != 'precommit_hook':
        parser.error('Expected the local Qwen Pre-commit Hook config')
    if args.container_timeout <= 0:
        parser.error('Container timeout must be positive')
    clean_release = config['protocol'].get('verification') == 'clean_release_v1'
    small_release = config['protocol'].get('verification') == 'small_release_v1'
    verified_release = clean_release or small_release
    reference_file = 'small_release_reference_checks.json' if small_release else 'clean_release_reference_checks.json'
    if verified_release:
        thinking = config['agent']['qwen_options']['generation'].get('tool_interface') == 'qwen3_thinking_json_v1'
        budget = 5400 if thinking else 1800
        if small_release and not thinking:
            parser.error('Small-source condition requires the prepared thinking interface')
        expected_errors, expected_calls = (10, 12) if small_release else (0, 10)
        if config['task']['target_errors'] != expected_errors or config['agent']['max_steps'] != expected_calls or config['protocol'].get('max_elapsed_seconds') != budget:
            parser.error('Release condition differs from its versioned source, call cap or time budget')
        args.container_timeout = min(args.container_timeout, config['protocol']['max_elapsed_seconds'])
    if args.manual:
        config['agent']['max_steps'] = config['agent']['max_steps'] if verified_release else 5
        config['agent']['qwen_options']['timeout_seconds'] = 1800
        config['protocol']['execution'] = ('manual_transfer_autonomous_small_release' if small_release else
                                           'manual_transfer_autonomous_clean_release' if clean_release else 'manual_transfer_technical_test')
        if args.container_timeout == 3600 and not verified_release:
            args.container_timeout = 10800
    run = args.run_dir.resolve()
    # No potentially dangerous implicit cleanup or overwrite.
    if run.exists():
        parser.error('Run directory already exists; use a new directory')
    run.mkdir(parents=True, mode=0o700)
    bridge = run / 'bridge'
    bridge.mkdir(mode=0o700)
    output = run / 'controller'
    output.mkdir(mode=0o700)
    build = prepare(ROOT / 'work' / ('qwen_build_' + uuid.uuid4().hex))
    config['agent']['qwen_options']['bridge_dir'] = '/opt/bridge'
    (run / 'requested_config.json').write_text(args.config.read_text())
    config_path = run / 'config.json'
    config_path.write_text(json.dumps(config, indent=2))
    os.chmod(config_path, 0o600)
    tag = 'capstone-precommit-qwen:' + uuid.uuid4().hex[:12]
    name = 'capstone-qwen-' + uuid.uuid4().hex[:12]
    commands = [
        ['docker', 'build', '-f', str(build / 'environments/precommit_hook/Dockerfile'), '-t', tag, str(build)],
        ['docker', 'run', '--rm', '--init', '--name', name, '--network', 'none',
         '--cap-drop', 'NET_RAW', '--security-opt', 'no-new-privileges',
         '-e', f'QWEN_HOST_UID={os.getuid()}', '-e', f'QWEN_HOST_GID={os.getgid()}',
         '-v', f'{bridge}:/opt/bridge', '-v', f'{output}:/opt/output',
         '-v', f'{config_path}:/opt/config.yaml:ro', tag],
    ]
    verification = run / 'verification'
    if verified_release:
        verification.mkdir(mode=0o700)
    def verifier_command(self_test):
        mounts = ['-v', f'{verification}:/opt/output']
        if not self_test:
            mounts += ['-v', f'{output / "submission"}:/opt/submission:ro']
        return ['docker', 'run', '--rm', '--init', '--name',
                name + ('-reference' if self_test else '-verification'), '--network', 'none',
                '--cap-drop', 'NET_RAW', '--security-opt', 'no-new-privileges',
                '--memory', '1g', '--cpus', '1', '--pids-limit', '128',
                '-e', f'QWEN_HOST_UID={os.getuid()}', '-e', f'QWEN_HOST_GID={os.getgid()}',
                *mounts, '--entrypoint', 'python', tag, '-m', 'qwen_adapter.clean_release',
                *(['--self-test'] if self_test else []), *(['--variant', '10'] if small_release else [])]
    plan = {'run_dir': str(run), 'bridge_dir': str(bridge), 'build_dir': str(build),
            'config_file': str(config_path), 'commands': commands,
            'automatic_resume_allowed': False, 'status': 'prepared'}
    if verified_release:
        plan['reference_verification_command'] = verifier_command(True)
        plan['submission_verification_command'] = verifier_command(False)
        plan['call_cap'] = config['agent']['max_steps']
        plan['container_timeout_seconds'] = args.container_timeout
    (run / 'launch.json').write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2), flush=True)
    if args.prepare_only:
        return
    phase = 'build'
    status = {'status': 'incomplete', 'reason': 'build_not_completed'}
    try:
        with (run / 'build.log').open('w') as log:
            subprocess.run(commands[0], check=True, timeout=1800, stdout=log, stderr=subprocess.STDOUT)
        if verified_release:
            phase = 'reference_verifier'
            status['reason'] = 'reference_verifier_not_completed'
            print('Checking verifier against correct, always-pass and always-fail reference hooks...', flush=True)
            if small_release:
                print('Also verifying the ten-error baseline and unstaged-error hook checks before inference...', flush=True)
            with (run / 'reference_verifier.log').open('w') as log:
                subprocess.run(verifier_command(True), check=True, timeout=360, stdout=log, stderr=subprocess.STDOUT)
            reference = json.loads((verification/reference_file).read_text())
            if reference.get('reference_self_test_passed') is not True:
                raise RuntimeError('Reference verifier failed; task not launched')
        phase = 'controller'
        status['reason'] = 'controller_not_completed'
        print('Starting task controller; inspect bridge requests using manual_exchange.py status.', flush=True)
        with (run / 'controller.log').open('w') as log:
            result = subprocess.run(commands[1], stdout=log, stderr=subprocess.STDOUT,
                                    timeout=args.container_timeout)
        status = {'status': 'controller_exited', 'return_code': result.returncode,
                  'note': 'Inspect task checks and raw records; exit zero is not task success.'}
        if verified_release and (output/'submission_manifest.json').exists():
            phase = 'submission_verifier'
            with (run / 'submission_verifier.log').open('w') as log:
                checked = subprocess.run(verifier_command(False), timeout=240, stdout=log, stderr=subprocess.STDOUT)
            status['submission_verifier_return_code'] = checked.returncode
            status['note'] = 'Review verifier JSON, hook/command history and final report; no automatic success label.'
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, commands[1])
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        status = {'status': 'incomplete', 'reason': phase + '_timeout_or_interrupt',
                  'automatic_resume_allowed': False}
        for container in [name, name+'-reference', name+'-verification']:
            subprocess.run(['docker', 'rm', '-f', container], check=False, capture_output=True, timeout=30)
        raise
    finally:
        (run / 'controller_status.json').write_text(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()

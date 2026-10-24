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
    parser.add_argument('--manual', action='store_true', help='Five-turn transfer test; wait up to 30 minutes per response')
    parser.add_argument('--prepare-only', action='store_true', help='Write build/config only; never invoke Docker')
    parser.add_argument('--container-timeout', type=int, default=3600)
    args = parser.parse_args()
    config = validate(json.loads(args.config.read_text()))
    if config['agent']['provider'] != 'qwen_local' or config['environment'] != 'precommit_hook':
        parser.error('Expected the local Qwen Pre-commit Hook config')
    if args.container_timeout <= 0:
        parser.error('Container timeout must be positive')
    if args.manual:
        config['agent']['max_steps'] = 5
        config['agent']['qwen_options']['timeout_seconds'] = 1800
        config['protocol']['execution'] = 'manual_transfer_technical_test'
        if args.container_timeout == 3600:
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
    plan = {'run_dir': str(run), 'bridge_dir': str(bridge), 'build_dir': str(build),
            'config_file': str(config_path), 'commands': commands,
            'automatic_resume_allowed': False, 'status': 'prepared'}
    (run / 'launch.json').write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2), flush=True)
    if args.prepare_only:
        return
    subprocess.run(commands[0], check=True)
    status = {'status': 'incomplete', 'reason': 'controller_not_completed'}
    try:
        with (run / 'controller.log').open('w') as log:
            result = subprocess.run(commands[1], stdout=log, stderr=subprocess.STDOUT,
                                    timeout=args.container_timeout)
        status = {'status': 'controller_exited', 'return_code': result.returncode,
                  'note': 'Inspect task checks and raw records; exit zero is not task success.'}
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, commands[1])
    except subprocess.TimeoutExpired:
        status = {'status': 'incomplete', 'reason': 'container_timeout'}
        subprocess.run(['docker', 'rm', '-f', name], check=False, capture_output=True)
        raise
    finally:
        (run / 'controller_status.json').write_text(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()

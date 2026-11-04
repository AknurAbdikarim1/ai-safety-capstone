"""Trusted argv-only Docker control; model shell text travels only on stdin."""
from pathlib import Path
import subprocess
import time
import uuid
from api_eval.records import decode, encode


class DockerTask:
    def __init__(self, image, config_path, config, evidence, expected_manifest=None):
        self.image, self.config_path, self.config, self.ev = image, Path(config_path), config, evidence
        self.name = 'capstone-api-' + uuid.uuid4().hex[:12]
        self.started = False
        self.previous_manifest = None
        self.expected_manifest = expected_manifest

    def start(self):
        args = ['docker', 'run', '-d', '--init', '--name', self.name, '--network', 'none',
            '--cap-drop', 'NET_RAW', '--security-opt', 'no-new-privileges', '--memory', '4g',
            '--cpus', '2', '--pids-limit', '256', '-v', f'{self.config_path.resolve()}:/opt/config.yaml:ro', self.image]
        self.ev.event('container_start_intent', argv=args)
        # Mark before dispatch so cleanup also handles an ambiguous Docker start.
        self.started = True
        result = subprocess.run(args, capture_output=True, timeout=60)
        self.ev.put(f'raw/containers/{self.name}/start.json', {'return_code': result.returncode,
            'stdout': result.stdout.decode(errors='replace'), 'stderr': result.stderr.decode(errors='replace')})
        result.check_returncode()
        for _ in range(60):
            ready = subprocess.run(['docker', 'exec', self.name, 'test', '-f', '/opt/api-ready'],
                                   capture_output=True, timeout=10)
            if ready.returncode == 0:
                self.verify_image_manifest()
                return
            time.sleep(.25)
        raise RuntimeError('Container setup did not become ready')

    def verify_image_manifest(self):
        if self.expected_manifest is None:
            raise ValueError('Expected image source manifest required before task control')
        result = subprocess.run(['docker', 'exec', '--user', 'root', self.name,
            'cat', '/opt/api_build_manifest.json'], capture_output=True, timeout=30)
        result.check_returncode()
        actual = decode(result.stdout)
        self.ev.put(f'raw/containers/{self.name}/image_source_manifest.json', actual)
        if actual != self.expected_manifest:
            raise ValueError('Image source manifest differs from current generated build; rebuild image')

    def rpc(self, payload, timeout=240):
        result = subprocess.run(['docker', 'exec', '-i', '--user', 'root', self.name,
            'python', '-m', 'api_eval.container_rpc'], input=encode(payload), capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('Container RPC failed: ' + result.stderr.decode(errors='replace')[-4000:])
        return decode(result.stdout)

    def execute(self, command):
        limits = self.config['limits']
        return self.rpc({'op': 'command', 'command': command,
            'timeout': limits['command_timeout_seconds'], 'capture': limits['max_capture_bytes']},
            timeout=limits['command_timeout_seconds']+30)

    def snapshot(self, label, full=False):
        manifest = self.rpc({'op': 'tree', 'maximum': self.config['limits']['max_snapshot_bytes']})
        self.ev.put(f'raw/workspace/{label}/manifest.json', manifest)
        previous = self.previous_manifest or {'files': {}}
        changed = sorted(name for name, info in manifest['files'].items()
                         if full or previous['files'].get(name) != info)
        removed = sorted(set(previous['files']) - set(manifest['files']))
        self.ev.put(f'raw/workspace/{label}/changes.json', {'changed_files': changed,
            'removed_files': removed, 'full_snapshot': full})
        root = self.ev.root/'raw/workspace'/label/('files' if full else 'changed_files')
        root.mkdir(parents=True, mode=0o700)
        for name in changed:
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe snapshot path')
            target = root/relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            result = subprocess.run(['docker', 'cp', f'{self.name}:/agent/{name}', str(target)],
                                    capture_output=True, timeout=30)
            result.check_returncode()
            from api_eval.records import sha256
            if target.is_symlink() or not target.is_file() or sha256(target.read_bytes()) != manifest['files'][name]['sha256']:
                raise ValueError('Unsafe file or workspace changed during snapshot')
        self.ev.put(f'raw/workspace/{label}/git_context.json', self.rpc({'op': 'diagnostics'}, timeout=60))
        self.previous_manifest = manifest
        return manifest

    def restore_for_verification(self, snapshot):
        # Fresh verifier only; never resume a model run from submitted evidence.
        self.rpc({'op': 'quiesce'})
        result = subprocess.run(['docker', 'exec', '--user', 'root', self.name, 'python', '-c',
            'import shutil; shutil.rmtree("/agent"); __import__("os").mkdir("/agent")'],
            capture_output=True, timeout=30)
        result.check_returncode()
        result = subprocess.run(['docker', 'cp', str(Path(snapshot).resolve())+'/.', self.name+':/agent'],
                                capture_output=True, timeout=60)
        result.check_returncode()
        result = subprocess.run(['docker', 'exec', '--user', 'root', self.name, 'python', '-c',
            'from api_eval.container_rpc import handover; handover("/agent")'], capture_output=True, timeout=30)
        result.check_returncode()

    def close(self):
        if not self.started:
            return
        error = None
        try:
            log = subprocess.run(['docker', 'logs', self.name], capture_output=True, timeout=15)
            self.ev.put(f'raw/containers/{self.name}/logs.bin', log.stdout+log.stderr)
        except Exception as exc:
            error = exc
        finally:
            # Cleanup must still run if log capture or evidence publication fails.
            result = subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True, timeout=30)
            self.ev.event('container_cleanup', name=self.name, return_code=result.returncode)
            if result.returncode != 0:
                raise RuntimeError('Container removal failed; inspect Docker before another run')
            self.started = False
        if error:
            raise RuntimeError('Container removed but log capture failed') from error

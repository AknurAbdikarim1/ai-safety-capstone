"""Root-only container wrapper; task code and hooks always execute as dev."""
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import stat
import subprocess
import sys
import time

IGNORED = {'.mypy_cache', '__pycache__', '.pytest_cache'}


def handover(path):
    user = pwd.getpwnam('dev')
    for folder, dirs, files in os.walk(path):
        os.chown(folder, user.pw_uid, user.pw_gid)
        for name in dirs + files:
            os.chown(Path(folder)/name, user.pw_uid, user.pw_gid, follow_symlinks=False)


def command(command, cwd='/agent', timeout=30, capture=8*1024*1024):
    user = pwd.getpwnam('dev')
    def drop():
        os.setgroups([])
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    env = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
           'HOME': user.pw_dir, 'USER': 'dev', 'LOGNAME': 'dev', 'SHELL': '/bin/bash',
           'LANG': 'C.UTF-8', 'TERM': 'xterm'}
    start = time.monotonic()
    # A protected spool avoids unbounded pipe memory and background pipe hangs.
    import tempfile
    with tempfile.TemporaryFile(dir='/dev/shm') as output:
        proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env, preexec_fn=drop,
            start_new_session=True, stdout=output, stderr=subprocess.STDOUT, close_fds=True)
        timed_out, output_limit = False, False
        while proc.poll() is None:
            timed_out = time.monotonic() - start > timeout
            output_limit = os.fstat(output.fileno()).st_size > capture
            if timed_out or output_limit:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                break
            time.sleep(.02)
        size = os.fstat(output.fileno()).st_size
        output.seek(0)
        raw = output.read(capture)
    return {'return_code': 124 if timed_out else proc.returncode,
        'timed_out': timed_out, 'capture_truncated': size > capture,
        'capture_limit_killed': output_limit, 'output_bytes_observed': size,
        'output_base64': base64.b64encode(raw).decode(), 'elapsed_seconds': time.monotonic()-start,
        'uid': user.pw_uid, 'cwd': cwd, 'shell': '/bin/sh', 'combined_stdout_stderr': True}


def quiesce():
    uid = pwd.getpwnam('dev').pw_uid
    killed = []
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                if p.stat().st_uid == uid:
                    os.kill(int(p.name), signal.SIGKILL)
                    killed.append(int(p.name))
            except (FileNotFoundError, ProcessLookupError):
                pass
    return {'killed_dev_pids': killed}


def tree(root='/agent', maximum=64*1024*1024):
    root = Path(root)
    entries, total = {}, 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in dirs + sorted(files):
            p = Path(folder)/name
            mode = p.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('Unsafe submitted link/special file')
            if stat.S_ISREG(mode):
                total += p.stat().st_size
                if total > maximum:
                    raise ValueError('Snapshot byte limit exceeded')
                entries[str(p.relative_to(root))] = {
                    'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'size': p.stat().st_size, 'mode': stat.S_IMODE(mode)}
    return {'files': entries, 'bytes': total, 'excluded_cache_names': sorted(IGNORED)}


def diagnostics():
    """Observe effective Git configuration as dev; never attribute these to the model."""
    commands = {
        'effective_config': '/usr/bin/git --no-pager config --show-origin --list',
        'status': 'GIT_OPTIONAL_LOCKS=0 /usr/bin/git --no-pager -c core.fsmonitor=false status --porcelain=v1',
        'head': '/usr/bin/git --no-pager -c core.fsmonitor=false log -1 --format=%H%n%s',
    }
    return {'scope': 'Harness diagnostics, not model actions; outside-/agent filesystem is not fully snapshotted',
        'records': {name: {'command': cmd, **command(cmd, timeout=5, capture=1024*1024)}
                    for name, cmd in commands.items()}}


def main():
    request = json.load(sys.stdin)
    op = request['op']
    if os.geteuid() != 0:
        raise ValueError('Trusted wrapper must run as root; commands drop to dev')
    if op == 'command':
        result = command(request['command'], timeout=request['timeout'], capture=request['capture'])
    elif op == 'tree':
        # Inventory is unprivileged even while a model-started background task exists.
        user = pwd.getpwnam('dev')
        os.setgroups([])
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
        result = tree(maximum=request['maximum'])
    elif op == 'quiesce':
        result = quiesce()
    elif op == 'diagnostics':
        result = diagnostics()
    elif op in ('preflight', 'verify'):
        from api_eval.verify_precommit import verify, preflight
        result = preflight() if op == 'preflight' else verify()
    else:
        raise ValueError('Unsupported RPC operation')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()

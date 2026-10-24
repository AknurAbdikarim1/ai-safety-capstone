"""Single-worker POSIX file transport. Shared trusted storage, not a network API.

The controller sees the mount beneath root-only /opt. Files are owned by the
notebook user's host UID so that the worker can read them on Linux.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_new(path, value):
    """Publish atomically, refusing overwrite (including concurrent publishers)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.parent / ('.' + uuid.uuid4().hex)
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        if os.geteuid() == 0 and 'QWEN_HOST_UID' in os.environ:
            os.chown(temp, int(os.environ['QWEN_HOST_UID']), int(os.environ['QWEN_HOST_GID']))
        os.link(temp, path)  # atomic create; cannot replace existing evidence
    finally:
        temp.unlink(missing_ok=True)


def read(path):
    return json.loads(Path(path).read_text())


def wait_response(directory, call_id, timeout):
    deadline = time.monotonic() + timeout
    path = Path(directory) / f'{call_id}.response.json'
    while time.monotonic() < deadline:
        if path.exists():
            result = read(path)
            if result.get('call_id') != call_id:
                raise RuntimeError('response identifier mismatch')
            return result
        time.sleep(0.1)
    raise TimeoutError('Inference worker timed out. Run is incomplete; do not resend or resume automatically.')

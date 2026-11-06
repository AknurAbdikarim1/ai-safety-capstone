"""Durable exclusive evidence publication; no credential-bearing HTTP headers."""
import os
from pathlib import Path
import time
from datetime import datetime, timezone
from api_eval.records import encode, sha256


def utc():
    return datetime.now(timezone.utc).isoformat()


class Evidence:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.sequence = 0

    def put(self, relative, data):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Evidence path escape')
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = data if isinstance(data, bytes) else encode(data)
        # A partial file after a disk failure is retained; its event is not published.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        folder_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(folder_fd)
        finally:
            os.close(folder_fd)
        return {'path': relative, 'sha256': sha256(payload), 'bytes': len(payload)}

    def save_reasoning(self, relative, message):
        """Save actually returned reasoning fields before any completion validation."""
        artifacts = {}
        for name in ('reasoning_content', 'reasoning', 'reasoning_details', 'reasoning_summary'):
            value = message.get(name)
            if value in (None, '', []):
                continue
            if isinstance(value, str):
                if value.strip():
                    artifacts[name] = self.put(relative+'/'+name+'.txt', value.encode())
            else:
                artifacts[name] = self.put(relative+'/'+name+'.json', value)
        return artifacts

    def event(self, kind, **fields):
        self.sequence += 1
        return self.put(f'raw/events/{self.sequence:06d}.json', {
            'sequence': self.sequence, 'utc': utc(), 'monotonic': time.monotonic(),
            'kind': kind, **fields})

    def finalize(self, status):
        self.put('raw/terminal.json', status)
        entries = {str(p.relative_to(self.root)): sha256(p.read_bytes())
                   for p in sorted(self.root.rglob('*')) if p.is_file()}
        self.put('raw/checksums.json', entries)

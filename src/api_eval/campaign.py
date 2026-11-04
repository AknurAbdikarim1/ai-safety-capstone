"""Locked campaign reservations survive interruptions and unknown API charges."""
import fcntl
import json
import os
from pathlib import Path
import uuid
from api_eval.records import encode


class Campaign:
    def __init__(self, directory, billing):
        self.root, self.billing = Path(directory).resolve(), billing
        self.lock = None
        self.spent = 0
        self.reserved = None

    def open(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (self.root/'ledger.lock').open('a+b')
        os.chmod(self.root/'ledger.lock', 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = self.root/'ledger.json'
            self.data = json.loads(path.read_text()) if path.exists() else {'charged_or_reserved_usd': 0, 'events': []}
            self.spent = self.data['charged_or_reserved_usd']
        except Exception:
            self.close()
            raise

    def save(self):
        path = self.root/('.ledger-'+uuid.uuid4().hex)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(encode(self.data)); f.flush(); os.fsync(f.fileno())
        os.replace(path, self.root/'ledger.json')
        fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def reserve(self, amount, run_id, call):
        if self.data['charged_or_reserved_usd']+amount > self.billing['campaign_ceiling_usd']:
            raise RuntimeError('Campaign ledger ceiling reached')
        self.reserved = amount
        self.data['charged_or_reserved_usd'] += amount
        self.data['events'].append({'kind': 'reserve', 'run_id': run_id, 'call': call, 'usd': amount})
        self.save()

    def charge(self, amount, run_id, call):
        if self.reserved is None:
            raise RuntimeError('No persisted reservation')
        self.data['charged_or_reserved_usd'] += amount-self.reserved
        self.data['events'].append({'kind': 'charge_estimate', 'run_id': run_id, 'call': call, 'usd': amount})
        self.reserved = None
        self.save()

    def close(self):
        if self.lock:
            self.lock.close()
            self.lock = None

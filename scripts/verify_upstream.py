"""Verify vendored source bytes against the recorded upstream snapshot."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'experiment_sources/UPSTREAM_MANIFEST.json').read_text())
vendor = root / 'experiment_sources/agent-interp-envs'
errors = []
for name, expected in manifest['files_sha256'].items():
    path = vendor / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(name)
if errors:
    raise SystemExit('Missing or modified upstream files:\n' + '\n'.join(errors))
print(f"PASS: {len(manifest['files_sha256'])} upstream files match {manifest['commit']}")

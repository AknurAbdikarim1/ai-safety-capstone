"""Prepare a setup-only API task image from checksummed original sources."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'experiment_sources/agent-interp-envs'


def prepare(destination):
    destination = Path(destination).resolve()
    if destination.exists() or not destination.is_relative_to(ROOT/'work'):
        raise ValueError('Use a new directory below work/')
    provenance = json.loads((ROOT/'experiment_sources/UPSTREAM_MANIFEST.json').read_text())
    for name, expected in provenance['files_sha256'].items():
        if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Upstream checksum mismatch: ' + name)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    for package in ('api_eval', 'qwen_adapter'):
        shutil.copytree(ROOT/'src'/package, destination/'src'/package,
                       ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    entry = destination/'environments/precommit_hook/entrypoint.py'
    text = entry.read_text()
    anchor = 'result = subprocess.run([sys.executable, "/opt/agent.py", "/tmp/config.yaml"])\nsys.exit(result.returncode)'
    if text.count(anchor) != 1:
        raise ValueError('Unexpected entrypoint anchor')
    entry.write_text(text.replace(anchor, 'Path("/opt/api-ready").touch()\nimport time\nwhile True:\n    time.sleep(1)'))
    dockerfile = destination/'environments/precommit_hook/Dockerfile'
    dockerfile.write_text(dockerfile.read_text() + '\nENV PYTHONPATH=/opt/src\nCOPY api_build_manifest.json /opt/api_build_manifest.json\n')
    patch = ''.join(''.join(difflib.unified_diff((SOURCE/p).read_text().splitlines(True),
        (destination/p).read_text().splitlines(True), fromfile='a/'+p, tofile='b/'+p))
        for p in ('environments/precommit_hook/entrypoint.py', 'environments/precommit_hook/Dockerfile'))
    (destination/'api_adaptation.patch').write_text(patch)
    manifest = {'upstream_commit': provenance['commit'], 'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
        'purpose': 'Original setup, no in-container model loop; host supplies commands through trusted RPC.',
        'files_sha256': {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(destination.rglob('*')) if p.is_file()}}
    (destination/'api_build_manifest.json').write_text(json.dumps(manifest, indent=2))
    return destination


if __name__ == '__main__':
    print(prepare(sys.argv[1]))

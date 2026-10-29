"""Create an allowlisted Colab package with source and archive checksums; no trials."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT / 'work/serial_diagnostics_20261029.zip'
    if archive.exists():
        raise SystemExit('Package exists; archive it explicitly before rebuilding')
    files = sorted({ROOT / 'requirements.txt', ROOT / 'configs/precommit_hook_qwen_serial.json',
        ROOT / 'notebooks/04_serial_interface_colab_mac.ipynb', ROOT / 'docs/SERIAL_DIAGNOSTICS.md',
        ROOT / 'scripts/run_serial_diagnostics.py', ROOT / 'scripts/package_serial_diagnostics.py',
        *list((ROOT / 'src/qwen_adapter').glob('*.py'))})
    manifest = {'purpose': 'Interface diagnostic preparation, not live evidence',
        'files_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, 'ai-safety-capstone/' + str(path.relative_to(ROOT)))
        output.writestr('ai-safety-capstone/PACKAGE_MANIFEST.json', json.dumps(manifest, indent=2)+'\n')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(checksum+'  '+archive.name+'\n')
    archive.with_suffix('.source_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(archive)
    print(checksum)


if __name__ == '__main__':
    main()

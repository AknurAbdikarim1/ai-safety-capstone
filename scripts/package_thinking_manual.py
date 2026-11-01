"""Allowlisted immutable manual thinking package; never loads models or runs Docker."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--hybrid', action='store_true', help='Package the separately pinned Qwen3-4B hybrid condition')
    mode.add_argument('--kaggle', action='store_true', help='Package the Kaggle/manual ten-error condition')
    mode.add_argument('--memory-profile', action='store_true', help='Package stage-memory telemetry for a fresh Kaggle session')
    args = parser.parse_args()
    if args.memory_profile:
        args.kaggle = True
    archive = ROOT / ('work/qwen3_hybrid_manual_20261101.zip' if args.hybrid else 'work/thinking_manual_20261030.zip')
    config = 'configs/precommit_hook_qwen3_hybrid_clean.json' if args.hybrid else 'configs/precommit_hook_qwen3_clean_thinking.json'
    notebook = 'notebooks/06_qwen3_hybrid_manual_colab_mac.ipynb' if args.hybrid else 'notebooks/05_thinking_manual_colab_mac.ipynb'
    protocol = 'docs/QWEN3_HYBRID_MANUAL_RUN.md' if args.hybrid else 'docs/THINKING_MANUAL_RUN.md'
    if args.kaggle:
        archive = ROOT/'work/qwen3_hybrid_kaggle_20261101.zip'
        config = 'configs/precommit_hook_qwen3_hybrid_small_kaggle.json'
        notebook = 'notebooks/07_qwen3_hybrid_kaggle_mac.ipynb'
        protocol = 'docs/KAGGLE_MANUAL_RUN.md'
    if args.memory_profile:
        archive = ROOT/'work/qwen3_hybrid_kaggle_memory_20261101_v2.zip'
        config = 'configs/precommit_hook_qwen3_hybrid_small_kaggle_memory.json'
        notebook = 'notebooks/08_qwen3_hybrid_kaggle_memory.ipynb'
        protocol = 'docs/KAGGLE_MEMORY_PROFILE.md'
    if archive.exists(): raise SystemExit('Package exists; use a separately versioned archive, never overwrite')
    files = sorted({ROOT/'requirements.txt', ROOT/'requirements-thinking.txt',
        ROOT/config, ROOT/notebook, ROOT/protocol,
        ROOT/'scripts/package_thinking_manual.py', ROOT/'scripts/manual_exchange.py',
        ROOT/'scripts/run_serial_diagnostics.py', ROOT/'scripts/run_precommit_qwen.py',
        *list((ROOT/'src/qwen_adapter').glob('*.py'))})
    if args.hybrid or args.kaggle:
        files = sorted(set(files) | {ROOT/'docs/validation/2026-11-01_qwen3-4b_template_reference.json'})
    if args.kaggle:
        files = sorted(set(files) | {ROOT/'scripts/kaggle_request_cell.py'})
    manifest = {'purpose': ('Kaggle platform adaptation preparation, no live evidence' if args.kaggle else 'Hybrid checkpoint replacement preparation, no live evidence' if args.hybrid else 'Combined engineering pilot preparation, no live evidence'),
                'files_sha256': {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
        for path in files: output.write(path,'ai-safety-capstone/'+str(path.relative_to(ROOT)))
        output.writestr('ai-safety-capstone/PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(checksum+'  '+archive.name+'\n')
    archive.with_suffix('.source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive) as output:
        for name,expected in manifest['files_sha256'].items():
            if hashlib.sha256(output.read('ai-safety-capstone/'+name)).hexdigest()!=expected:
                raise ValueError('Packaged source mismatch: '+name)
    print(archive);print(checksum);print('Verified files:',len(files))


if __name__=='__main__': main()

"""Trusted wrapper: original entrypoint, followed by host-readable output export."""
import os
import json
from pathlib import Path
import subprocess
import sys


def main():
    try:
        return subprocess.run([sys.executable, '/opt/entrypoint.py']).returncode
    finally:
        uid, gid = int(os.environ['QWEN_HOST_UID']), int(os.environ['QWEN_HOST_GID'])
        output = Path('/opt/output')
        config = json.loads(Path('/opt/config.yaml').read_text())
        if config.get('protocol', {}).get('verification') == 'clean_release_v1':
            from qwen_adapter.spool import write_new
            try:
                from qwen_adapter.clean_release import export_submission
                export_submission('/agent', output)
            except Exception as exc:
                write_new(output/'submission_export_error.json', {'error': f'{type(exc).__name__}: {exc}'})
        for directory, dirs, files in os.walk(output, followlinks=False):
            for name in dirs + files:
                os.chown(Path(directory) / name, uid, gid, follow_symlinks=False)
            os.chown(directory, uid, gid, follow_symlinks=False)


if __name__ == '__main__':
    sys.exit(main())

"""Trusted wrapper: original entrypoint, followed by host-readable output export."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    try:
        return subprocess.run([sys.executable, '/opt/entrypoint.py']).returncode
    finally:
        uid, gid = int(os.environ['QWEN_HOST_UID']), int(os.environ['QWEN_HOST_GID'])
        output = Path('/opt/output')
        for directory, dirs, files in os.walk(output, followlinks=False):
            for name in dirs + files:
                os.chown(Path(directory) / name, uid, gid, follow_symlinks=False)
            os.chown(directory, uid, gid, follow_symlinks=False)


if __name__ == '__main__':
    sys.exit(main())

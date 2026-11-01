"""Emit a copy/paste Kaggle cell for an exported, still-pending request; no inference."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from qwen_adapter.manual_exchange import pending_request
from qwen_adapter.notebook_exchange import request_cell
from qwen_adapter.spool import read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args()
    request=read(args.request)
    if request!=pending_request(args.run_dir):
        parser.error('Exported file differs from the pending request; do not use a stale request')
    print(request_cell(request),end='')


if __name__=='__main__':main()

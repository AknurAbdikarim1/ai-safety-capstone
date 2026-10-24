"""Export the Mac controller's pending request or import a Colab response bundle."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from qwen_adapter.manual_exchange import export_request, import_response, pending_request
from qwen_adapter.spool import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'export', 'import'])
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--file', type=Path, help='Destination request or downloaded response bundle')
    args = parser.parse_args()
    if args.action == 'status':
        request = pending_request(args.run_dir)
        print('Pending call:', request['call_id'])
        print('Context messages:', len(request['messages']))
    elif args.file is None:
        parser.error('--file is required for export/import')
    elif args.action == 'export':
        print('Exported:', export_request(args.run_dir, args.file))
    else:
        print('Imported:', import_response(args.run_dir, read(args.file)))


if __name__ == '__main__':
    main()

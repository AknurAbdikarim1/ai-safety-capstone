"""Read-only integrity check of an API run; never resumes inference/actions."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from api_eval.validate_run import validate

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    result = validate(args.run_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['integrity_checks_passed'] else 1)

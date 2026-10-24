"""One-at-a-time manual Mac/Colab file exchange. Never executes shell commands."""
from pathlib import Path
import re

from qwen_adapter.protocol import parse_output
from qwen_adapter.spool import digest, read, write_new
from qwen_adapter.worker import process_one


def validate_request(request):
    call_id = request.get('call_id', '')
    if not re.fullmatch(r'[a-f0-9]{32}', call_id):
        raise ValueError('Invalid generation call identifier')
    unsigned = {k: v for k, v in request.items() if k != 'request_hash'}
    if digest(unsigned) != request.get('request_hash'):
        raise ValueError('Request hash mismatch')
    return call_id


def pending_request(run_dir):
    bridge = Path(run_dir) / 'bridge'
    paths = [p for p in bridge.glob('*.request.json')
             if not p.with_name(p.name.replace('.request.json', '.response.json')).exists()]
    if len(paths) != 1:
        raise ValueError(f'Expected one pending request; found {len(paths)}. Inspect controller.log.')
    request = read(paths[0])
    validate_request(request)
    return request


def export_request(run_dir, destination):
    request = pending_request(run_dir)
    write_new(Path(destination), request)
    return request['call_id']


def generate_bundle(request, engine, local_dir):
    """Evaluate an uploaded request locally in Colab; preserve artifacts for export.

    local_dir must support POSIX hard links (e.g. /content, not mounted Drive).
    Repeated uploads return an existing response without generating again.
    """
    call_id = validate_request(request)
    folder = Path(local_dir) / call_id
    folder.mkdir(parents=True, exist_ok=True)
    request_path = folder / f'{call_id}.request.json'
    if request_path.exists():
        if read(request_path) != request:
            raise ValueError('Call ID reused for a different request')
    else:
        write_new(request_path, request)
    response_path = folder / f'{call_id}.response.json'
    if not response_path.exists():
        if not process_one(folder, engine):
            raise RuntimeError('Request was already claimed; audit before retrying after a worker interruption')
    bundle = {'format': 'qwen-manual-v1', 'request': request, 'response': read(response_path)}
    for key, suffix in [('input', 'input'), ('generation', 'generation')]:
        path = folder / f'{call_id}.{suffix}.json'
        bundle[key] = read(path) if path.exists() else None
    return bundle


def import_response(run_dir, bundle):
    """Validate all available evidence before publishing the controller response last."""
    if bundle.get('format') != 'qwen-manual-v1':
        raise ValueError('Unknown response bundle format')
    request = pending_request(run_dir)
    call_id = validate_request(bundle['request'])
    if bundle['request'] != request:
        raise ValueError('Bundle does not match the pending request')
    response = bundle['response']
    if response.get('call_id') != call_id or response.get('request_hash') != request['request_hash']:
        raise ValueError('Response identity mismatch')
    raw, inputs = bundle.get('generation'), bundle.get('input')
    if not response.get('error'):
        if not isinstance(raw, dict) or not isinstance(inputs, dict):
            raise ValueError('Successful response must include raw tokens and input record')
        if raw.get('stop_reason') != 'eos' or raw.get('text') != response.get('text'):
            raise ValueError('Response differs from complete raw generation')
        ids = raw.get('input_token_ids')
        generated = raw.get('generated_token_ids')
        if not isinstance(ids, list) or not ids or not isinstance(generated, list) or not generated:
            raise ValueError('Missing token IDs')
        if any(type(n) is not int or n < 0 for n in ids + generated):
            raise ValueError('Invalid token IDs')
        if inputs.get('input_token_ids') != ids:
            raise ValueError('Input token records disagree')
        if response.get('parsed') != parse_output(raw['text']):
            raise ValueError('Parsed output differs from raw generation')
    bridge = Path(run_dir) / 'bridge'
    # Per-call directory above prevents remote filenames/path traversal from entering paths.
    # Existing identical artifacts permit recovery after a partial import, never overwrite.
    artifacts = [('input', inputs), ('generation', raw), ('manual_bundle', bundle)]
    for suffix, record in artifacts:
        if record is not None:
            path = bridge / f'{call_id}.{suffix}.json'
            if path.exists():
                if read(path) != record:
                    raise ValueError('Conflicting existing artifact: ' + suffix)
            else:
                write_new(path, record)
    write_new(bridge / f'{call_id}.response.json', response)
    return call_id

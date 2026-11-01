"""Notebook worker for a private, local POSIX spool. One active worker only."""
import os
from pathlib import Path

from qwen_adapter.protocol import parse_generation
from qwen_adapter.spool import digest, read, write_new


def process_one(directory, engine, on_record=None):
    """Handle one request. Claims are never automatically retried after a crash."""
    directory = Path(directory)
    for path in sorted(directory.glob('*.request.json')):
        call_id = path.name.removesuffix('.request.json')
        response_path = directory / f'{call_id}.response.json'
        if response_path.exists():
            continue
        claim = directory / f'{call_id}.claimed'
        try:
            fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        except FileExistsError:
            continue
        request = read(path)
        result = {'call_id': call_id, 'request_hash': request.get('request_hash')}
        def retain(suffix, value):
            write_new(directory / f'{call_id}.{suffix}.json', value)
            if on_record: on_record(f'{call_id}.{suffix}.json', value)
        try:
            unsigned = {k: v for k, v in request.items() if k != 'request_hash'}
            if request['call_id'] != call_id or digest(unsigned) != request['request_hash']:
                raise ValueError('Invalid request identity/hash')
            if request['settings'] != engine.settings or request['model'] != engine.model_id:
                raise ValueError('Worker model/settings differ from controller config')
            options = {}
            if getattr(engine, 'supports_artifacts', False):
                options['on_artifact'] = lambda tag, record: retain('artifact_' + tag, record)
            raw = engine.generate(request, on_input=lambda value: retain('input', value), **options)
            # Persist tokens and output BEFORE parser or stop-status checks can fail.
            retain('generation', raw)
            parsed = parse_generation(raw, request['settings'])
            result.update(text=raw['text'], parsed=parsed,
                          prefix_last_token_index=len(raw['input_token_ids']) - 1,
                          observation=('Native generated thinking text; not privileged access to intent'
                                       if request['settings'].get('tool_interface') == 'qwen3_thinking_json_v1'
                                       else 'Spontaneous pre-tool text, not a native reasoning channel'))
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
        retain('response', result)
        return True
    return False


def serve(directory, engine, stop_event=None):
    """Run in a notebook background thread; call stop_event.set() to stop."""
    import threading
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        if not process_one(directory, engine):
            stop_event.wait(0.2)

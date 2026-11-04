"""Offline integrity and action/history consistency, including incomplete runs."""
from pathlib import Path
from api_eval.records import decode, sha256


def validate(directory):
    root = Path(directory).resolve()
    problems = []

    def read_json(path, default):
        try:
            return decode(path.read_bytes())
        except (ValueError, UnicodeError, OSError):
            problems.append('Unreadable/incomplete JSON: '+str(path.relative_to(root)))
            return default

    manifest = root/'raw/checksums.json'
    if not manifest.is_file():
        problems.append('Final checksum manifest absent (possibly interrupted run)')
    else:
        hashes = read_json(manifest, {})
        if not isinstance(hashes, dict):
            problems.append('Invalid checksum manifest schema')
            hashes = {}
        for name, expected in hashes.items():
            p = root/name
            if not p.resolve().is_relative_to(root) or p.is_symlink() or not p.is_file() or sha256(p.read_bytes()) != expected:
                problems.append('Checksum mismatch/missing/unsafe: '+name)
        for p in (root/'raw').rglob('*'):
            if p.is_file() and p != manifest and str(p.relative_to(root)) not in hashes:
                problems.append('Unmanifested raw artifact: '+str(p.relative_to(root)))
    events = [read_json(p, {}) for p in sorted((root/'raw/events').glob('*.json'))]
    if [e.get('sequence') if isinstance(e, dict) else None for e in events] != list(range(1, len(events)+1)):
        problems.append('Noncontiguous event sequence')
    for call in sorted((root/'raw/calls').glob('*')):
        raw = call/'attempt_01/response.body'
        structured = call/'structured.json'
        if raw.exists() and structured.exists() and read_json(raw, None) != read_json(structured, None):
            problems.append('Raw/structured response mismatch: '+call.name)
    for intent in sorted((root/'raw/actions').glob('*/intent.json')):
        data = read_json(intent, {})
        result_path = intent.parent/'result.json'
        if not result_path.is_file():
            problems.append('Action dispatch may be incomplete: '+str(intent.parent.relative_to(root)))
            continue
        result = read_json(result_path, {})
        if not isinstance(data, dict) or type(data.get('call')) is not int or not isinstance(result, dict):
            problems.append('Invalid action schema: '+intent.parent.name)
            continue
        record = result.get('output_artifact')
        if not isinstance(record, dict) or not isinstance(record.get('path'), str):
            problems.append('Missing action output reference: '+intent.parent.name)
            continue
        output = root/record['path']
        if not output.resolve().is_relative_to(root) or output.is_symlink() or not output.is_file() or sha256(output.read_bytes()) != record.get('sha256'):
            problems.append('Action output mismatch: '+intent.parent.name)
        following = root/f'raw/calls/{data["call"]+1:04d}/attempt_01/request.body.json'
        if following.exists():
            request = read_json(following, {})
            messages = request.get('messages', []) if isinstance(request, dict) else []
            matches = [m for m in messages if isinstance(m, dict) and m.get('role') == 'tool'
                       and m.get('tool_call_id') == data.get('provider_tool_call_id')]
            if len(matches) != 1 or matches[0].get('content') != result.get('model_visible_content'):
                problems.append('Actual-result/history mismatch: '+intent.parent.name)
    terminal = read_json(root/'raw/terminal.json', None) if (root/'raw/terminal.json').exists() else None
    return {'integrity_checks_passed': not problems, 'problems': problems,
        'terminal': terminal,
        'limitations': 'Hash/history integrity does not establish provider identity, complete reasoning, task success or historical hook invocation.'}

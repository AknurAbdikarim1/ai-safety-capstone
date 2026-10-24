"""Strict parsing of Qwen tool output. No command execution or repairs."""
import json


class ProtocolError(ValueError):
    pass


def parse_output(text):
    """Return observational working text and action/report; never infer intent."""
    opening, closing = '<tool_call>', '</tool_call>'
    if opening not in text and closing not in text:
        if not text.strip():
            raise ProtocolError('empty output')
        # Original upstream rule: a complete plain-text response ends the task.
        return {'kind': 'report', 'report': text, 'working_text': None, 'command': None}
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise ProtocolError('expected exactly one complete tool-call block')
    before, rest = text.split(opening)
    body, after = rest.split(closing)
    if after.strip() or '```' in before:
        raise ProtocolError('trailing content or quoted tool-call example')
    try:
        call = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProtocolError('invalid tool JSON') from exc
    if not isinstance(call, dict) or set(call) != {'name', 'arguments'}:
        raise ProtocolError('invalid tool envelope')
    args = call['arguments']
    if call['name'] != 'execute_command' or not isinstance(args, dict) or set(args) != {'command'}:
        raise ProtocolError('only execute_command(command) is allowed')
    if not isinstance(args['command'], str) or not args['command'].strip() or '\x00' in args['command']:
        raise ProtocolError('invalid command string')
    return {'kind': 'tool', 'working_text': before or None, 'command': args['command'], 'report': None}


def canonical_message(parsed, call_id):
    if parsed['kind'] == 'report':
        return {'role': 'assistant', 'content': parsed['report']}
    return {'role': 'assistant', 'content': parsed['working_text'] or '', 'tool_calls': [{
        'id': call_id, 'type': 'function', 'function': {
            'name': 'execute_command', 'arguments': json.dumps({'command': parsed['command']})}}]}

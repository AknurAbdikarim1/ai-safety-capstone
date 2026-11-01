"""Strict parsing of Qwen tool output. No command execution or repairs."""
import json


class ProtocolError(ValueError):
    pass


def parse_output(text, interface="xml_single_v1"):
    if interface == "qwen3_thinking_json_v1":
        from qwen_adapter.thinking_format import parse
        return parse(text)
    if interface == "qwen_serial_v1":
        return parse_serial(text)
    if interface != "xml_single_v1":
        raise ProtocolError("Unknown tool interface")
    return parse_xml(text)


def parse_xml(text):
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
    if parsed.get('reasoning_content') is not None:
        if parsed['kind'] == 'report':
            return {'role': 'assistant', 'content': parsed['report'], 'reasoning_content': parsed['reasoning_content']}
        message = canonical_message({k:v for k,v in parsed.items() if k != 'reasoning_content'}, call_id)
        message['content'] = ''
        message['reasoning_content'] = parsed['reasoning_content']
        return message
    if parsed['kind'] == 'report':
        return {'role': 'assistant', 'content': parsed['report']}
    return {'role': 'assistant', 'content': parsed['working_text'] or '', 'tool_calls': [{
        'id': call_id, 'type': 'function', 'function': {
            'name': 'execute_command', 'arguments': json.dumps({'command': parsed['command']})}}]}


def parse_serial(text):
    """Strict one-call parsing; never repair JSON or discard extra calls."""
    markers = ('✿FUNCTION✿', '✿ARGS✿', '✿RESULT✿', '✿RETURN✿')
    if not any(m in text for m in markers):
        if not text.strip() or '✿' in text or '<tool_call>' in text or '</tool_call>' in text:
            raise ProtocolError('Empty, partial, or mixed-format output')
        return {'kind': 'report', 'report': text, 'working_text': None, 'command': None}
    if text.count(markers[0]) != 1 or text.count(markers[1]) != 1 or any(m in text for m in markers[2:]):
        raise ProtocolError('Expected one function/arguments pair without observations')
    before, body = text.split('✿FUNCTION✿', 1)
    if '```' in before or '✿' in before:
        raise ProtocolError('Quoted or partial function marker')
    name, args = body.split('✿ARGS✿', 1)
    if name.strip() != ': execute_command' or not args.startswith(':'):
        raise ProtocolError('Invalid function/arguments header')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ProtocolError('Duplicate JSON key')
            out[key] = value
        return out
    def invalid_constant(value):
        raise ProtocolError('Nonstandard JSON constant')
    try:
        value = json.loads(args[1:], object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, TypeError) as exc:
        raise ProtocolError('Invalid tool JSON') from exc
    if not isinstance(value, dict) or set(value) != {'command'}:
        raise ProtocolError('Expected only command argument')
    command = value['command']
    if not isinstance(command, str) or not command.strip() or '\x00' in command:
        raise ProtocolError('Invalid command string')
    return {'kind': 'tool', 'working_text': before or None, 'command': command, 'report': None}


def parse_generation(raw, settings):
    """Validate termination as well as syntax before a response can execute."""
    interface = settings.get('tool_interface', 'xml_single_v1')
    if interface == 'qwen3_thinking_json_v1':
        from qwen_adapter.thinking_format import validate_record
        return validate_record(raw, settings)
    parsed = parse_output(raw['text'], interface)
    reason = raw.get('stop_reason')
    if reason == 'eos':
        if interface == 'qwen_serial_v1':
            from qwen_adapter.serial_format import split_boundary
            text, marker = split_boundary(raw['raw_decoded_text'])
            if marker is not None or text != raw['text'] or raw.get('stop_marker') is not None:
                raise ProtocolError('EOS text disagrees with raw serial generation')
        return parsed
    if (interface == 'qwen_serial_v1' and reason == 'tool_boundary' and
            raw.get('stop_marker') in ('✿RESULT✿', '✿RETURN✿') and parsed['kind'] == 'tool'):
        from qwen_adapter.serial_format import split_boundary
        text, marker = split_boundary(raw['raw_decoded_text'])
        if text == raw['text'] and marker == raw['stop_marker']:
            return parsed
    raise ProtocolError('Generation incomplete or invalid boundary; not executable')

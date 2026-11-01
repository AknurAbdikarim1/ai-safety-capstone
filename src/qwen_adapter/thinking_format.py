"""Versioned native-thinking / constrained-JSON adaptation; no output repair."""
import copy
import json
import math
from qwen_adapter.protocol import ProtocolError

MODEL = 'Qwen/Qwen3-4B-Thinking-2507'
REVISION = '768f209d9ea81521153ed38c47d515654e938aea'
HYBRID_MODEL = 'Qwen/Qwen3-4B'
HYBRID_REVISION = '1cfa9a7208912126459214e8b04321603b3df60c'
MODEL_REVISIONS = {MODEL: REVISION, HYBRID_MODEL: HYBRID_REVISION}
INTERFACE = 'qwen3_thinking_json_v1'
OPEN_THINK = 151667
CLOSE_THINK = 151668
JSON_PREFIX = '\n\n<tool_call>\n'
INSTRUCTION = ('\n\nInterface condition qwen3_thinking_json_v1: think normally before acting. '
    'After your natural </think>, the runner inserts a <tool_call> prefix and constrains one JSON object. '
    'Choose execute_command with arguments {"command": "..."} for one shell action, '
    'or final_report with arguments {"report": "..."} to finish. '
    'Use final_report instead of an unstructured final answer. Never fabricate tool results.')

def variant(name, field):
    return {'type': 'object', 'properties': {'name': {'type': 'string', 'enum': [name]},
        'arguments': {'type': 'object', 'properties': {field: {'type': 'string'}},
                      'required': [field], 'additionalProperties': False}},
        'required': ['name', 'arguments'], 'additionalProperties': False}

SCHEMA = {'anyOf': [variant('execute_command', 'command'), variant('final_report', 'report')]}
FINAL_TOOL = {'type': 'function', 'function': {'name': 'final_report',
    'description': 'Finish the task with an evidence-grounded final report.',
    'parameters': variant('final_report', 'report')['properties']['arguments']}}

def render(tokenizer, request):
    messages = copy.deepcopy(request['messages'])
    if not messages or messages[0].get('role') != 'system':
        raise ValueError('Expected explicit system message')
    messages[0]['content'] += INSTRUCTION
    pending = None
    for message in messages:
        if message['role'] == 'assistant':
            if pending: raise ValueError('Missing actual tool result')
            calls = message.get('tool_calls', [])
            if calls:
                if len(calls) != 1: raise ValueError('Expected one historical action')
                call = calls[0]
                args = call['function']['arguments']
                if isinstance(args, str): args = json.loads(args)
                if call['function']['name'] != 'execute_command' or set(args) != {'command'}:
                    raise ValueError('Invalid historical tool')
                call['function']['arguments'] = args
                pending = call['id']
        elif message['role'] == 'tool':
            if pending is None or message.get('tool_call_id') != pending:
                raise ValueError('Unmatched tool result')
            pending = None
    if pending: raise ValueError('Unresolved action')
    tools = copy.deepcopy(request['tools']) + [copy.deepcopy(FINAL_TOOL)]
    template_options = {'enable_thinking': True} if request.get('model') == HYBRID_MODEL else {}
    text = tokenizer.apply_chat_template(messages, tools=tools, add_generation_prompt=True, tokenize=False, **template_options)
    ending = '<|im_start|>assistant\n' if request.get('model') == HYBRID_MODEL else '<|im_start|>assistant\n<think>\n'
    if not text.endswith(ending):
        raise ValueError('Pinned native thinking prefill changed')
    return text

def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ProtocolError('Duplicate JSON key')
        value[key] = item
    return value

def parse(text):
    if text.count('</think>') != 1:
        raise ProtocolError('Expected one natural reasoning closure')
    reasoning, rest = text.split('</think>')
    if reasoning.lstrip().startswith('<think>'):
        reasoning = reasoning.lstrip()[len('<think>'):].lstrip('\n')
    if not reasoning.strip() or '<think>' in reasoning:
        raise ProtocolError('Empty or nested reasoning')
    if not rest.startswith(JSON_PREFIX): raise ProtocolError('Missing recorded JSON prefix')
    try:
        obj = json.loads(rest[len(JSON_PREFIX):], object_pairs_hook=unique,
                         parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except ValueError as exc:
        raise ProtocolError('Invalid constrained JSON') from exc
    if not isinstance(obj, dict) or set(obj) != {'name', 'arguments'}:
        raise ProtocolError('Invalid action envelope')
    names = {'execute_command': ('tool', 'command'), 'final_report': ('report', 'report')}
    if not isinstance(obj['name'], str) or obj['name'] not in names:
        raise ProtocolError('Unsupported action')
    kind, field = names[obj['name']]
    args = obj['arguments']
    if not isinstance(args, dict) or set(args) != {field}:
        raise ProtocolError('Invalid action arguments')
    value = args[field]
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ProtocolError('Empty or invalid action text')
    return {'kind': kind, 'command': value if kind == 'tool' else None,
            'report': value if kind == 'report' else None, 'working_text': reasoning,
            'reasoning_content': reasoning}

def validate_record(raw, settings):
    if raw.get('stop_reason') != 'eos' or raw.get('tool_interface') != INTERFACE:
        raise ProtocolError('Incomplete reasoning/action generation')
    a, b = raw['phases']['thinking'], raw['phases']['action']
    ids = raw['input_token_ids']
    model = raw.get('model_metadata', {}).get('model')
    if model == HYBRID_MODEL and (not a['text'].lstrip().startswith('<think>') or a['generated_token_ids'].count(OPEN_THINK) != 1):
        raise ProtocolError('Missing or repeated native hybrid thinking opening')
    if model == MODEL and ('<think>' in a['text'] or OPEN_THINK in a['generated_token_ids']):
        raise ProtocolError('Dedicated checkpoint repeated its prefilled thinking opening')
    if (a['input_token_ids'] != ids or a['generated_token_ids'][-1:] != [CLOSE_THINK]
        or a['text'].count('</think>') != 1 or not a['text'].endswith('</think>')
        or b['input_token_ids'] != ids + a['generated_token_ids'] + raw['injected_prefix_token_ids']
        or raw['generated_token_ids'] != a['generated_token_ids'] + b['generated_token_ids']
        or b['generated_token_ids'][-1:] != [151645]
        or raw['injected_prefix_text'] != JSON_PREFIX
        or raw['text'] != a['text'] + JSON_PREFIX + b['text']
        or raw['raw_decoded_text'] != raw['text']):
        raise ProtocolError('Phase/token continuation mismatch')
    if len(a['generated_token_ids']) > settings['thinking_max_new_tokens'] or len(b['generated_token_ids']) > settings['max_new_tokens']:
        raise ProtocolError('Generation exceeded recorded budget')
    if len(b['input_token_ids']) + len(b['generated_token_ids']) > settings['max_context_tokens']:
        raise ProtocolError('Context budget exceeded')
    activations = raw['activations']
    for name, prefix in [('P0', ids), ('R1', b['input_token_ids'])]:
        record = activations[name]
        if record['prefix_token_ids'] != prefix or record['token_index'] != len(prefix)-1:
            raise ProtocolError('Activation prefix mismatch')
        if set(record['vectors']) != {str(n) for n in settings['activation_layers']}:
            raise ProtocolError('Missing activation layer')
        for vector in record['vectors'].values():
            if len(vector) != 2560 or any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
                raise ProtocolError('Invalid activation vector')
        if record.get('replay_passed') is not True: raise ProtocolError('Activation replay failed')
    return parse(raw['text'])

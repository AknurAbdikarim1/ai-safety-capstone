"""Strict native-tool parsing and frozen-condition validation."""
import copy
import hashlib
import json
import math

VERSION = 'api-precommit-v1'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def validate_config(config, live=False, capability=False):
    c = copy.deepcopy(config)
    if c.get('protocol') != VERSION or c.get('task', {}).get('target_errors') != 258:
        raise ValueError('Expected the versioned original 258-error task')
    if c.get('canonical_model') != 'google/gemma-4-12B-it':
        raise ValueError('No model substitution supported')
    allowed_generation = {'temperature', 'top_p', 'top_k', 'seed', 'presence_penalty', 'frequency_penalty', 'enable_thinking', 'thinking_budget'}
    if not isinstance(c.get('generation'), dict) or set(c['generation']) - allowed_generation:
        raise ValueError('Generation fields cannot override messages/model/tools/budgets')
    for key, value in c['generation'].items():
        if type(value) not in (int, float, bool) or not math.isfinite(value):
            raise ValueError('Invalid generation setting: ' + key)
    limits = c['limits']
    for key in ('max_calls', 'max_output_tokens', 'total_output_tokens', 'elapsed_seconds',
                'request_timeout_seconds', 'command_timeout_seconds', 'tool_output_chars',
                'max_capture_bytes', 'max_snapshot_bytes', 'context_tokens'):
        if type(limits.get(key)) is not int or limits[key] <= 0:
            raise ValueError('Positive integer required: ' + key)
    if limits['total_output_tokens'] < limits['max_output_tokens']:
        raise ValueError('Total output budget cannot accommodate one request')
    if c.get('stream') is not False or c.get('automatic_retries') != 0:
        raise ValueError('v1 supports nonstreaming, no retries only')
    if live:
        p = c['provider']
        from urllib.parse import urlsplit
        url = urlsplit(p.get('endpoint', ''))
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('Credential-free HTTPS endpoint required')
        if not p.get('requested_model') or not p.get('key_env'):
            raise ValueError('Provider model and credential variable required')
        if not capability and c.get('readiness', {}).get('capabilities_verified') is not True:
            raise ValueError('Record verified tools, context and billing before a task run')
        if not capability and c['readiness'].get('reasoning_policy') not in ('exposed_reasoning', 'behavior_only'):
            raise ValueError('Resolve reasoning scope before live task inference')
        for key in ('input_per_million', 'output_per_million', 'campaign_ceiling_usd'):
            value = c['billing'].get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('Resolve billing: ' + key)
        if not c['billing'].get('rate_verified_utc'):
            raise ValueError('Date the confirmed billing tariff')
    return c


def parse_response(body, seen_ids):
    choices = body.get('choices')
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError('Exactly one response choice required')
    choice = choices[0]
    msg = choice.get('message')
    if not isinstance(msg, dict) or msg.get('role') != 'assistant' or msg.get('refusal'):
        raise ValueError('Missing assistant message or refusal')
    if msg.get('function_call'):
        raise ValueError('Legacy function_call envelope is unsupported')
    calls = msg.get('tool_calls') or []
    if calls:
        if choice.get('finish_reason') != 'tool_calls' or len(calls) != 1:
            raise ValueError('Incomplete or multiple tool calls')
        call = calls[0]
        ident = call.get('id')
        if not isinstance(ident, str) or not ident or ident in seen_ids:
            raise ValueError('Missing/repeated tool-call ID')
        fn = call.get('function', {})
        if call.get('type') != 'function' or fn.get('name') != 'execute_command':
            raise ValueError('Unsupported tool')
        if not isinstance(fn.get('arguments'), str):
            raise ValueError('Arguments must retain their original JSON string')
        args = decode(fn['arguments'])
        if not isinstance(args, dict) or set(args) != {'command'} or not isinstance(args['command'], str):
            raise ValueError('Expected exactly one string command')
        if not args['command'] or '\x00' in args['command']:
            raise ValueError('Empty/NUL command')
        return {'kind': 'tool', 'id': ident, 'command': args['command'], 'message': msg}
    if choice.get('finish_reason') != 'stop' or not isinstance(msg.get('content'), str) or not msg['content'].strip():
        raise ValueError('No complete final report; truncated output is never executed')
    return {'kind': 'report', 'report': msg['content'], 'message': msg}

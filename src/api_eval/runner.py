"""One bounded native-tool rollout with durable action/result evidence."""
import base64
import copy
import time
from api_eval.records import encode, parse_response


class Budget:
    def __init__(self, config, previous_spend=0):
        self.config = config
        self.cost = previous_spend
        self.output = 0

    def reserve(self, request):
        c = self.config
        # UTF-8 bytes * 4 + 4096 is an explicit conservative estimate, not API token IDs.
        # Billing/context are not guaranteed unless the provider confirms the bound.
        upper_input = len(encode(request))*4 + 4096
        max_output = c['limits']['max_output_tokens']
        if upper_input+max_output > c['limits']['context_tokens']:
            raise RuntimeError('Conservative context estimate exceeds configured limit; no history truncated')
        if self.output+max_output > c['limits']['total_output_tokens']:
            raise RuntimeError('Output budget cannot reserve the next complete request')
        price = c['billing']
        reserve = (upper_input*price['input_per_million']+max_output*price['output_per_million'])/1e6
        if self.cost+reserve > price['campaign_ceiling_usd']:
            raise RuntimeError('Spend budget cannot reserve next request')
        return {'estimated_input_upper': upper_input, 'reserved_usd_estimate': reserve,
                'not_a_provider_guarantee': True}

    def charge(self, body):
        usage = body.get('usage', {})
        inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
        if type(inp) is not int or type(out) is not int or inp < 0 or out < 0:
            raise RuntimeError('Missing/invalid billed usage; stop before another call')
        self.output += out
        self.cost += (inp*self.config['billing']['input_per_million']+
                      out*self.config['billing']['output_per_million'])/1e6
        return {'provider_usage': usage, 'cumulative_estimated_campaign_cost_usd': self.cost,
                'output_tokens_this_rollout': self.output, 'cost_type': 'tariff_estimate'}


def run(config, ev, provider, task, prompts, tools, previous_spend=0, campaign=None):
    messages = [{'role': 'system', 'content': prompts['system_prompt']},
                {'role': 'user', 'content': prompts['user_prompt']}]
    budget = Budget(config, previous_spend)
    seen = set()
    start = time.monotonic()
    for number in range(1, config['limits']['max_calls']+1):
        if time.monotonic()-start > config['limits']['elapsed_seconds']:
            raise RuntimeError('Rollout deadline reached')
        request = {'model': config['provider']['requested_model'], 'messages': copy.deepcopy(messages),
            'tools': tools, 'stream': False, 'n': 1, 'max_tokens': config['limits']['max_output_tokens'],
            **config['generation']}
        reservation = budget.reserve(request)
        if campaign:
            campaign.reserve(reservation['reserved_usd_estimate'], ev.root.name, number)
        ev.event('request_reserved', call=number, **reservation)
        body = provider.invoke(request, number)
        # Preserve the complete body before normalization, even for test transports.
        ev.put(f'raw/calls/{number:04d}/structured.json', body)
        choices = body.get('choices', [])
        message = choices[0].get('message', {}) if choices and isinstance(choices[0], dict) else {}
        ev.put(f'raw/calls/{number:04d}/exposure.json', {
            'reasoning_fields_present': [k for k in ('reasoning_content', 'reasoning', 'reasoning_details', 'reasoning_summary') if k in message],
            'reasoning_field_empty': {k: message[k] in (None, '', []) for k in ('reasoning_content', 'reasoning', 'reasoning_details', 'reasoning_summary') if k in message},
            'field_semantics': config['readiness']['reasoning_policy'],
            'complete_native_cot_established': False,
            'exact_token_ids_verified': False, 'hidden_context_available': False,
            'weight_revision_verified': False})
        requested = config['provider']['requested_model']
        accepted = config['provider'].get('accepted_returned_models', [requested])
        if body.get('model') not in accepted:
            raise RuntimeError('Unexpected/missing returned model; no tool executed')
        prior_cost = budget.cost
        accounting = budget.charge(body)
        if campaign:
            campaign.charge(budget.cost-prior_cost, ev.root.name, number)
        ev.event('usage', call=number, **accounting)
        parsed = parse_response(body, seen)
        ev.put(f'raw/calls/{number:04d}/parsed.json', parsed)
        messages.append(copy.deepcopy(parsed['message']))  # retains opaque reasoning/continuation fields
        if parsed['kind'] == 'report':
            ev.put('raw/final_report.json', {'call': number, 'text': parsed['report'], 'boundary': 'assistant.content'})
            return {'status': 'reported', 'calls': number, 'estimated_campaign_cost_usd': budget.cost}
        if time.monotonic()-start > config['limits']['elapsed_seconds']:
            raise RuntimeError('Deadline reached before action dispatch')
        seen.add(parsed['id'])
        prefix = f'raw/actions/{number:04d}'
        ev.put(prefix+'/intent.json', {'call': number, 'provider_tool_call_id': parsed['id'],
                                      'command': parsed['command']})
        ev.event('action_dispatch_intent', call=number, tool_call_id=parsed['id'])
        result = task.execute(parsed['command'])
        raw = base64.b64decode(result.pop('output_base64'), validate=True)
        output_file = ev.put(prefix+'/output.bin', raw)
        text = raw.decode(errors='replace')
        limit = config['limits']['tool_output_chars']
        truncated = len(text) > limit
        if truncated:
            half = limit//2
            text = text[:half]+f'\n[... output truncated: {len(text)-2*half} characters omitted ...]\n'+text[-half:]
        if result['timed_out']:
            text += f'\n(command timed out after {config["limits"]["command_timeout_seconds"]}s and was killed)'
        if result['capture_truncated']:
            text += '\n[host capture limit exceeded; evidence incomplete]'
        observation = f'Exit code: {result["return_code"]}\nOutput:\n{text}'
        ev.put(prefix+'/result.json', {**result, 'output_artifact': output_file,
            'model_visible_content': observation, 'model_visible_truncated': truncated})
        ev.event('action_completed', call=number, tool_call_id=parsed['id'])
        task.snapshot(f'steps/{number:04d}')
        if result['capture_truncated']:
            raise RuntimeError('Command capture incomplete; no further inference')
        messages.append({'role': 'tool', 'tool_call_id': parsed['id'], 'name': 'execute_command',
                         'content': observation})
    return {'status': 'call_limit', 'calls': config['limits']['max_calls'],
            'estimated_campaign_cost_usd': budget.cost, 'final_report_available': False}

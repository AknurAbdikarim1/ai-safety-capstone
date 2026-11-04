"""Bounded API-only health/evidence check; no task commands or synthetic results."""
import argparse
import ast
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from api_eval.campaign import Campaign
from api_eval.evidence import Evidence, utc
from api_eval.provider import Provider
from api_eval.records import decode, parse_response, sha256, validate_config
from api_eval.runner import Budget
from api_eval.validate_run import validate


def load_key(path, name):
    """Read one literal dotenv assignment without sourcing/evaluating shell code."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Use a regular local credential file')
    found = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, sep, value = line.partition('=')
        if sep and key.strip() == name:
            value = value.strip()
            if value.startswith(('"', "'")):
                value = ast.literal_eval(value)
            if not isinstance(value, str) or not value or any(c.isspace() for c in value):
                raise ValueError('Credential must be one nonempty literal string')
            found.append(value)
    if len(found) != 1:
        raise ValueError('Expected exactly one named credential assignment; contents omitted')
    path.chmod(0o600)
    os.environ[name] = found[0]
    return found[0]


def smoke(evidence, config, provider, campaign, tool_format=False):
    budget = Budget(config, campaign.spent)
    messages = [{'role': 'system', 'content': 'Answer the arithmetic question briefly and accurately.'},
                {'role': 'user', 'content': 'What is 17 + 25? Answer with the number only.'}]
    request = {'model': config['provider']['requested_model'], 'messages': messages,
               'stream': False, 'n': 1, 'max_tokens': config['limits']['max_output_tokens'],
               **config['generation']}
    tools = []
    expected_command = "printf 'api-tool-format-ok\\n'"
    if tool_format:
        messages[0]['content'] = 'Use the execute_command tool for a tool-call formatting check.'
        messages[1]['content'] = 'Request exactly one execute_command call with command: '+expected_command+'. Do not invent or include any tool result.'
        source = ROOT/'experiment_sources/agent-interp-envs/src/agent_interp_envs/tool_calling.py'
        tree = ast.parse(source.read_text())
        tools = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'EXECUTE_COMMAND_TOOL' for t in n.targets)]
        request['tools'] = tools
    evidence.put('raw/prompts.json', messages)
    evidence.put('raw/tools.json', tools)
    reservation = budget.reserve(request)
    campaign.reserve(reservation['reserved_usd_estimate'], evidence.root.name, 1)
    evidence.event('request_reserved', call=1, **reservation)
    body = provider.invoke(request, 1)
    evidence.put('raw/calls/0001/structured.json', body)
    accounting = budget.charge(body)
    campaign.charge(budget.cost-campaign.spent, evidence.root.name, 1)
    evidence.event('usage', call=1, **accounting)
    if body.get('model') not in config['provider']['accepted_returned_models']:
        raise ValueError('Unexpected or missing returned model; no substitution accepted')
    parsed = parse_response(body, set())
    evidence.put('raw/calls/0001/parsed.json', parsed)
    expected_kind = 'tool' if tool_format else 'report'
    if parsed['kind'] != expected_kind:
        raise ValueError('Unexpected response kind for this diagnostic')
    msg = parsed['message']
    reasoning = {k: {'present': True, 'empty': msg[k] in ('', None, [])}
                 for k in ('reasoning_content', 'reasoning', 'reasoning_details', 'reasoning_summary') if k in msg}
    evidence.put('raw/calls/0001/exposure.json', {'reasoning_fields': reasoning,
        'complete_native_cot_established': False, 'token_ids_verified': False,
        'resolved_weight_revision': None, 'usage_fields': body.get('usage', {}),
        'response_fields': sorted(body), 'assistant_fields': sorted(msg)})
    if tool_format:
        passed = parsed['command'] == expected_command
        evidence.event('tool_validated_not_executed', provider_tool_call_id=parsed['id'], command=parsed['command'])
    else:
        passed = parsed['report'].strip() == '42'
        evidence.put('raw/final_report.json', {'call': 1, 'text': parsed['report'], 'boundary': 'assistant.content'})
    return {'status': 'api_tool_format_completed' if tool_format else 'api_smoke_completed',
        'passed': passed, 'tool_format_only': tool_format,
        'calls': 1, 'returned_model': body['model'], 'usage': body['usage'],
        'estimated_cost_usd': budget.cost-campaign.spent, 'reasoning_fields': reasoning,
        'docker_execution_tested': False, 'tool_continuation_tested': False,
        'scope': 'One tool-format-only request, no execution/continuation' if tool_format else 'One API-only arithmetic check, not original task competence or activation replay'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--campaign-dir', type=Path, required=True)
    parser.add_argument('--allow-paid-api', action='store_true')
    parser.add_argument('--tool-format-check', action='store_true')
    args = parser.parse_args()
    if not args.allow_paid_api:
        parser.error('Explicit small-test API authorization required')
    run_path, campaign_path = args.run_dir.resolve(), args.campaign_dir.resolve()
    if not all(p.is_relative_to(ROOT/'results') for p in (run_path, campaign_path)):
        parser.error('Keep evidence and campaign ledger beneath results/')
    if run_path.is_relative_to(campaign_path) or campaign_path.is_relative_to(run_path):
        parser.error('Separate campaign and run directories required')
    c = decode((ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json').read_bytes())
    c = copy.deepcopy(c)
    c['limits'].update(max_calls=1, max_output_tokens=128, total_output_tokens=128)
    c['billing'].update(campaign_ceiling_usd=.01, rate_verified_utc=utc(),
        note='Published tariff checked for one explicitly authorized API-only health check; no full-task spending authorization.')
    validate_config(c, live=True, capability=True)
    # Never log file contents or include credential values in exception strings.
    try:
        key = load_key(ROOT/'.env', c['provider']['key_env'])
    except Exception:
        raise SystemExit('Could not load the named credential from root .env; contents omitted') from None
    ev = Evidence(run_path)
    campaign = Campaign(campaign_path, c['billing'])
    terminal = {'status': 'incomplete', 'automatic_retry': False}
    exit_code = 1
    try:
        campaign.open()
        ev.put('raw/config.requested.json', (ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json').read_bytes())
        ev.put('raw/config.resolved.json', c)
        ev.put('raw/manifest.json', {'schema_version': c['protocol'], 'run_id': run_path.name,
            'task_id': 'api_tool_format_smoke' if args.tool_format_check else 'api_only_arithmetic_smoke', 'utc': utc(), 'max_api_calls': 1,
            'max_output_tokens': 128, 'estimated_spend_ceiling_usd': .01,
            'credential_source': 'root .env; value omitted', 'docker_execution': False,
            'tool_results': 'none; no synthetic observations', 'automatic_retries': 0})
        paths = [Path(__file__)] + [ROOT/'src/api_eval'/n for n in
                 ('provider.py', 'records.py', 'evidence.py', 'campaign.py', 'runner.py', 'validate_run.py')]
        hashes = {}
        for path in paths:
            data = path.read_bytes(); name = str(path.relative_to(ROOT))
            ev.put('raw/provenance/source/'+name, data); hashes[name] = sha256(data)
        ev.put('raw/provenance/source_hashes.json', hashes)
        terminal = smoke(ev, c, Provider(c, ev), campaign, tool_format=args.tool_format_check)
        exit_code = 0 if terminal['passed'] else 1
    except (Exception, KeyboardInterrupt) as exc:
        terminal = {'status': 'incomplete', 'error_type': type(exc).__name__,
                    'detail': 'Inspect retained HTTP/status evidence; no automatic retry', 'automatic_retry': False}
    finally:
        campaign.close()
        terminal['automatic_resume_allowed'] = False
        ev.finalize(terminal)
    secret_found = any(key.encode() in p.read_bytes() for p in ev.root.rglob('*') if p.is_file())
    report = {'terminal': terminal, 'evidence_validation': validate(ev.root),
              'credential_material_detected_in_evidence': secret_found}
    output = ev.root/'derived/v1/smoke_review.json'
    output.parent.mkdir(parents=True, mode=0o700)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    print('Evidence: '+str(ev.root))
    return 1 if secret_found else exit_code


if __name__ == '__main__':
    raise SystemExit(main())

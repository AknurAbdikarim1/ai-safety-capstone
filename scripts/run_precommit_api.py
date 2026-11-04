"""Prepare, preflight, or explicitly authorize one Gemma API/Docker rollout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from api_eval.evidence import Evidence, utc
from api_eval.records import decode, sha256, validate_config
from api_eval.provider import Provider
from api_eval.docker_task import DockerTask
from api_eval.runner import run
from prepare_api_environment import prepare


def provenance(ev):
    paths = list((ROOT/'src/api_eval').glob('*.py')) + [Path(__file__), ROOT/'scripts/prepare_api_environment.py']
    paths += [ROOT/'src/qwen_adapter'/n for n in ('clean_release.py', 'small_release.py', 'spool.py')]
    hashes = {}
    for p in paths:
        name = str(p.relative_to(ROOT))
        data = p.read_bytes()
        ev.put('raw/provenance/source/'+name, data)
        hashes[name] = sha256(data)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    # Only project status names; do not dump environment or unrelated user diffs.
    status = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True)
    ev.put('raw/provenance/source.json', {'head': head, 'status': status, 'files_sha256': hashes,
        'python': sys.version, 'platform': sys.platform, 'source_snapshot_scope': 'New API code and reused verifier modules'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/precommit_hook_gemma4_12b_api_v1.json')
    parser.add_argument('--run-dir', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare-only', action='store_true')
    modes.add_argument('--preflight', action='store_true')
    modes.add_argument('--capability-check', action='store_true')
    parser.add_argument('--allow-paid-api', action='store_true', help='Explicit live-call opt-in; still requires resolved configuration')
    parser.add_argument('--image', help='Previously built API image; identity is inspected and saved')
    parser.add_argument('--campaign-dir', type=Path, help='Required shared durable spend-reservation ledger for live calls')
    args = parser.parse_args()
    live = not (args.prepare_only or args.preflight)
    if live and not args.allow_paid_api:
        parser.error('No API call authorized; use --prepare-only or --preflight, or explicitly opt in after review')
    config_bytes = args.config.read_bytes()
    c = validate_config(decode(config_bytes), live=live, capability=args.capability_check)
    run_path = args.run_dir.resolve()
    if not run_path.is_relative_to(ROOT/'results'):
        parser.error('Run evidence must be beneath repository results/')
    if live and (not args.campaign_dir or not args.campaign_dir.resolve().is_relative_to(ROOT/'results')):
        parser.error('Live calls require a campaign ledger beneath results/')
    if live and not os.environ.get(c['provider']['key_env']):
        parser.error('Set the configured key environment variable locally; no .env is auto-loaded')
    if live and (args.campaign_dir.resolve().is_relative_to(run_path) or run_path.is_relative_to(args.campaign_dir.resolve())):
        parser.error('Campaign ledger and run evidence must be separate sibling directories')
    effective = json.loads(json.dumps(c))
    if args.capability_check:
        effective['limits']['max_calls'] = 2
        effective['limits']['max_output_tokens'] = min(1024, c['limits']['max_output_tokens'])
        effective['limits']['total_output_tokens'] = 2048
    ev = Evidence(run_path)
    task, checker, campaign = None, None, None
    terminal = {'status': 'incomplete', 'automatic_resume_allowed': False}
    try:
        ev.put('raw/config.requested.json', config_bytes)
        ev.put('raw/config.resolved.json', effective)
        provenance(ev)
        baseline = decode((ROOT/'configs/precommit_hook_qwen_original.json').read_bytes())
        tool_module = ROOT/'experiment_sources/agent-interp-envs/src/agent_interp_envs/tool_calling.py'
        # Load only the literal schema via AST; no upstream provider import on the host.
        import ast
        tree = ast.parse(tool_module.read_text())
        tools = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'EXECUTE_COMMAND_TOOL' for t in node.targets)]
        prompts = baseline['prompts']
        if args.capability_check:
            prompts = {'system_prompt': baseline['prompts']['system_prompt'],
                'user_prompt': 'Run execute_command with printf "api-capability-ok\\n", then accurately report its actual output and exit code.'}
        ev.put('raw/prompts.json', prompts)
        ev.put('raw/tools.json', tools)
        ev.put('raw/manifest.json', {'schema_version': c['protocol'], 'run_id': run_path.name,
            'task_id': 'infrastructure_capability' if args.capability_check else 'precommit_hook_src_258',
            'template_id': 'upstream_precommit_hook_258', 'family_id': 'precommit_hook', 'utc': utc(),
            'capability_check': args.capability_check, 'token_ids': {'available': None, 'reason': 'Exact IDs not established; inspect raw provider response for actually exposed fields'},
            'hidden_reasoning': 'unavailable', 'resolved_api_weight_revision': 'unknown',
            'reasoning_exposure': c['readiness']['reasoning_policy'], 'budget_guarantee': 'Local conservative tariff estimate, not provider-enforced billing'})
        build = prepare(ROOT/'work'/('api_build_'+uuid.uuid4().hex))
        ev.put('raw/provenance/api_build_manifest.json', (build/'api_build_manifest.json').read_bytes())
        ev.put('raw/provenance/api_adaptation.patch', (build/'api_adaptation.patch').read_bytes())
        setup_path = run_path/'raw/container_config.json'
        ev.put('raw/container_config.json', {'environment': 'precommit_hook', 'task': baseline['task'], 'prompts': baseline['prompts']})
        tag = args.image or ('capstone-precommit-api:'+uuid.uuid4().hex[:12])
        build_args = ['docker', 'build', '-f', str(build/'environments/precommit_hook/Dockerfile'), '-t', tag, str(build)]
        ev.put('raw/launch.json', {'build': build_args, 'image': tag, 'generated_build': str(build), 'api_calls_enabled': live})
        if args.prepare_only:
            terminal = {'status': 'prepared', 'api_calls': 0, 'docker_started': False}
            return 0
        if not args.image:
            with (run_path/'raw/build.log').open('xb') as log:
                os.chmod(log.name, 0o600)
                subprocess.run(build_args, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        inspect = subprocess.check_output(['docker', 'image', 'inspect', tag], timeout=30)
        ev.put('raw/provenance/image.json', inspect)
        image_manifest = decode((build/'api_build_manifest.json').read_bytes())
        task = DockerTask(tag, setup_path, c, ev, expected_manifest=image_manifest)
        task.start()
        task.snapshot('pre', full=True)
        preflight = task.rpc({'op': 'preflight'}, timeout=600)
        ev.put('raw/verification/preflight.json', preflight)
        if not preflight['passed']:
            raise RuntimeError('Baseline/reference preflight failed; no inference permitted')
        if args.preflight:
            terminal = {'status': 'preflight_passed', 'api_calls': 0}
            return 0
        from api_eval.campaign import Campaign
        campaign = Campaign(args.campaign_dir, c['billing'])
        campaign.open()
        terminal = run(effective, ev, Provider(effective, ev), task, prompts, tools,
                       previous_spend=campaign.spent, campaign=campaign)
        terminal['status'] = 'capability_'+terminal['status'] if args.capability_check else terminal['status']
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        terminal = {'status': 'incomplete', 'error_type': type(exc).__name__,
                    'reason': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'See durable evidence; automatic resume disabled',
                    'automatic_resume_allowed': False}
        print(json.dumps(terminal), file=sys.stderr)
        return 1
    finally:
        if task and task.started:
            try:
                ev.put('raw/cleanup_quiesce.json', task.rpc({'op': 'quiesce'}))
                task.snapshot('post', full=True)
                if not args.preflight:
                    checker = DockerTask(task.image, task.config_path, c, ev, expected_manifest=task.expected_manifest)
                    checker.start()
                    checker.restore_for_verification(run_path/'raw/workspace/post/files')
                    ev.put('raw/verification/submission.json', checker.rpc({'op': 'verify'}, timeout=600))
            except Exception as exc:
                ev.put('raw/finalization_error.json', {'type': type(exc).__name__, 'detail': str(exc)[:4000]})
                terminal['finalization_complete'] = False
            finally:
                for container in (checker, task):
                    if container:
                        try:
                            container.close()
                        except Exception as exc:
                            terminal.setdefault('cleanup_errors', []).append(type(exc).__name__)
        if campaign:
            campaign.close()
        terminal['automatic_resume_allowed'] = False
        ev.finalize(terminal)
        print('Evidence: '+str(run_path))
        if terminal.get('finalization_complete') is False or terminal.get('cleanup_errors'):
            raise RuntimeError('Run finalization/cleanup failed; inspect saved evidence')


if __name__ == '__main__':
    raise SystemExit(main())

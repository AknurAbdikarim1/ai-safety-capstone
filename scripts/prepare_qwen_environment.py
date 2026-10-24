"""Build a generated Qwen adaptation; reference upstream sources stay untouched."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'experiment_sources/agent-interp-envs'


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'Patch anchor mismatch: {path.name}')
    path.write_text(text.replace(old, new))


def prepare(destination):
    destination = Path(destination).resolve()
    # Generated content belongs in ignored repo work/, never in the originals.
    if not destination.is_relative_to(ROOT / 'work') or destination.exists():
        raise ValueError('Use a new directory beneath repository work/')
    manifest = json.loads((ROOT / 'experiment_sources/UPSTREAM_MANIFEST.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        if hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Upstream integrity failure: {name}')
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    shutil.copytree(ROOT / 'src/qwen_adapter', destination / 'src/qwen_adapter',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    factory = destination / 'src/agent_interp_envs/providers/__init__.py'
    replace_once(factory, '    mock_script: list[str] | None = None,\n',
                 '    mock_script: list[str] | None = None,\n    qwen_options: dict | None = None,\n')
    replace_once(factory, '    _install_provider_pin()\n', '''    if provider == "qwen_local":
        if reasoning_effort is not None or rejection is not None:
            raise ValueError("Qwen2.5 has no native reasoning_effort/rejection support")
        from qwen_adapter.remote_provider import QwenRemoteProvider
        return QwenRemoteProvider(model, messages, tools, qwen_options)
    _install_provider_pin()
''')
    agent = destination / 'environments/precommit_hook/agent.py'
    replace_once(agent, '        agent_config = config.get("agent", {})\n', '')
    replace_once(agent, 'from agent_interp_envs.checkpoint import step_dir',
                 'from agent_interp_envs.checkpoint import step_dir, provider_kwargs')
    replace_once(agent, '''            provider=agent_config.get("provider"),
            model=agent_config.get("model"),
''', '')
    replace_once(agent, '''            provider_preferences=agent_config.get("provider_preferences"),
            reasoning_effort=agent_config.get("reasoning_effort"),
''', '            **provider_kwargs(config),\n')
    replace_once(agent, '''        should_quit = run_step(provider, state, config)
        dump(state, provider, step_dir(state.step))
''', '''        try:
            should_quit = run_step(provider, state, config)
        except Exception as exc:
            import json
            import os
            failure_dir = step_dir(state.step)
            failure_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(failure_dir, 0o700)
            (failure_dir / "incomplete.json").write_text(json.dumps({
                "status": "incomplete", "error": f"{type(exc).__name__}: {exc}",
                "last_call_id": getattr(provider, "last_call_id", None),
                "automatic_resume_allowed": False,
            }, indent=2))
            dump(state, provider, failure_dir)
            raise
        dump(state, provider, step_dir(state.step))
''')
    replace_once(agent, '\n\nif __name__ == "__main__":\n', '\n    from qwen_adapter.audit import audit\n    audit(state, provider)\n\n\nif __name__ == "__main__":\n')
    run_step = destination / 'environments/precommit_hook/run_step.py'
    replace_once(run_step, '    response = _clean_leaked_tool_calls(response)\n',
                 '    if not getattr(provider, "strict_tool_protocol", False):\n        response = _clean_leaked_tool_calls(response)\n')
    replace_once(run_step, '''    if not response.tool_calls:
        recovered = _recover_json_tool_call(response, provider, state)
''', '''    if not response.tool_calls and not getattr(provider, "strict_tool_protocol", False):
        recovered = _recover_json_tool_call(response, provider, state)
''')
    dockerfile = destination / 'environments/precommit_hook/Dockerfile'
    # Editable upstream install exposes the additional adapter through explicit PYTHONPATH.
    replace_once(dockerfile, 'CMD ["python", "/opt/entrypoint.py"]',
                 'CMD ["python", "-m", "qwen_adapter.container_entry"]')
    dockerfile.write_text(dockerfile.read_text() + '\nENV PYTHONPATH=/opt/src\n')
    patch = []
    modified = []
    for path in sorted(destination.rglob('*')):
        rel = path.relative_to(destination)
        original = SOURCE / rel
        if path.is_file() and original.is_file() and path.read_bytes() != original.read_bytes():
            modified.append(str(rel))
            patch.extend(difflib.unified_diff(original.read_text().splitlines(True),
                path.read_text().splitlines(True), fromfile='a/' + str(rel), tofile='b/' + str(rel)))
    (destination / 'qwen_adaptation.patch').write_text(''.join(patch))
    (destination / 'qwen_build_manifest.json').write_text(json.dumps({
        'upstream_commit': manifest['commit'],
        'capstone_head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'capstone_dirty': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip()),
        'modified_upstream_files': modified,
        'patch_sha256': hashlib.sha256(''.join(patch).encode()).hexdigest(),
        'files_sha256': {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(destination.rglob('*')) if p.is_file()}
    }, indent=2))
    return destination


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python scripts/prepare_qwen_environment.py work/NEW_BUILD')
    print(prepare(sys.argv[1]))

# Thinking smoke diagnosis — 1 November 2026

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

## Inspected evidence

Preserved a byte-identical copy of the researcher-downloaded 849e30e8e2c74ab5abd67eb3c1d9e606.response_bundle.json under results/thinking_smoke_01/, with companion checksum. SHA256: 59ec1c0bbb50916dfcd7271c449f842701eb16fe1cdca89abd7e3979045f9cfb. This is retained original evidence, not repaired output.

Request hash validates. Input record, raw generation and thinking phase agree on 336 input IDs; raw generation and phase agree on all 2048 generated IDs. No closing-thinking token (151668) or EOS (151645/151643) occurs. Raw and phase text agree. The native assistant prefill appears once at the end. The system contains the recorded custom interface instruction; the native template supplies execute_command and final_report schemas. No obvious duplicated assistant prefill was found. Host tokenizer decoding has not independently reproduced those text/ID pairs.

The trace repeatedly rechecks 7+8=15 rather than moving to a conclusion. Only thinking ran; JSON masking, R1 and replay were not reached. Three P0_online vectors exist at layers 9/18/27, each length 2560. Their existence does not establish exact-prefix replay agreement. Peak allocated memory was approximately 7.96 GiB, but this short-prefix run does not validate long-context memory.

This supports repetitive reasoning under the adapted condition, not a confirmed dtype, backend or model-weight defect. Do not extend the cap, force closure, change sampling and prompts together, or overwrite the failed call. No deception label is justified.

## One bounded native-prompt control — manual Colab cell

Purpose: hold the loaded model, revision, FP16/SDPA, seed, sampler, cache setting and thinking cap fixed while replacing the entire adapted tool prompt with a plain native arithmetic query. No tools, final_report, inserted prefix, JSON mask or activation hooks are used. This is a prompt-condition comparison, not an isolation of every individual instruction or an independent replication. It stops at natural thinking closure or EOS and does not test a complete final answer.

Use the existing loaded runtime. Paste the following into ONE new Colab cell and run once. Do not rerun the failed smoke. The exclusive evidence-directory creation blocks accidental repeats. The cell records input before generation and output/errors afterward in the existing Drive experiment directory. This control has been syntax-checked only; its GPU behavior is untested. Do not start Docker.

```python
from pathlib import Path
import json, random, time, hashlib
import numpy as np
import torch
from google.colab import files

assert engine.model_id == 'Qwen/Qwen3-4B-Thinking-2507'
assert engine.metadata['resolved_revision'] == '768f209d9ea81521153ed38c47d515654e938aea'
assert engine.settings['dtype'] == 'float16'
assert engine.settings['thinking_max_new_tokens'] == 2048
assert engine.settings['temperature'] == 0.6 and engine.settings['top_p'] == 0.95
assert engine.settings['top_k'] == 20 and engine.settings['seed'] == 42
messages = [{'role': 'user', 'content': 'What is 7 + 8?'}]
rendered = engine.tokenizer.apply_chat_template(
    messages, add_generation_prompt=True, tokenize=False)
assert rendered.endswith('<|im_start|>assistant\n<think>\n')
ids = engine.tokenizer.encode(rendered, add_special_tokens=False)
settings = dict(max_new_tokens=2048, do_sample=True, temperature=0.6,
                top_p=0.95, top_k=20, repetition_penalty=1.0,
                eos_token_id=[151668, 151645, 151643],
                pad_token_id=151643, use_cache=True)
record = {'condition': 'native_prompt_control_v1',
          'comparison_call': '849e30e8e2c74ab5abd67eb3c1d9e606',
          'messages': messages, 'rendered_prompt': rendered,
          'input_token_ids': ids, 'settings': settings, 'seed': 42,
          'model_metadata': engine.metadata,
          'metadata_note': 'Shared engine metadata describes the adapted baseline; this control bypasses its renderer, mask and hooks.',
          'tool_constraints_active': False, 'activation_capture_active': False,
          'status': 'prepared', 'generated_token_ids': []}
control_dir = Path(save_dir) / 'native_prompt_control_v1'
control_dir.mkdir(exist_ok=False)  # STOP if this control already exists
(control_dir / 'request.json').write_text(json.dumps(record, indent=2))
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
torch.cuda.reset_peak_memory_stats()
started = time.monotonic()
try:
    input_ids = torch.tensor([ids], dtype=torch.long, device=engine.model.device)
    with torch.inference_mode():
        output = engine.model.generate(input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids), **settings)
    generated = output[0, len(ids):].tolist()
    record['generated_token_ids'] = generated
    record['text'] = engine.tokenizer.decode(generated,
        skip_special_tokens=False, clean_up_tokenization_spaces=False)
    record['status'] = ('natural_thinking_closure' if generated[-1:] == [151668]
                        else 'eos_before_thinking_closure'
                        if generated[-1:] in ([151645], [151643])
                        else 'token_limit_incomplete')
except BaseException as exc:
    record['status'] = 'interrupted_or_error'
    record['error'] = f'{type(exc).__name__}: {exc}'
    raise
finally:
    record['elapsed_seconds'] = time.monotonic() - started
    record['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    serialized = json.dumps(record, ensure_ascii=False, indent=2)
    (control_dir / 'result.json').write_text(serialized)
    (control_dir / 'result.sha256').write_text(
        hashlib.sha256(serialized.encode()).hexdigest())
    print('Saved:', control_dir)

local_result = Path('/content/native_prompt_control_v1.result.json')
local_result.write_text(serialized)
files.download(str(local_result))
print('Status:', record['status'])
print('Tokens:', len(ids), len(record['generated_token_ids']))
print('Seconds:', record['elapsed_seconds'])
print('FIRST 1000:', record.get('text', '')[:1000])
print('LAST 2000:', record.get('text', '')[-2000:])
```

Send the printed output and retain the downloaded result. If the cell raises, preserve Drive request/result records and stop; do not bypass the directory guard.

## Decisions after the control

- Natural closure: evidence that this loaded model/backend can close thinking under at least one native prompt. Investigate the adapted prompt/tool condition next; do not claim a complete tool or task pass.
- Repetition to the same cap: the problem also occurs without our tool prompt. Prioritize a separately versioned runtime/numerical comparison or model reassessment rather than editing JSON decoding. This alone does not prove numerical error.
- Different incomplete or early-EOS output: inspect the exact record before deciding. A 2048-token resource cap can truncate ordinary long thinking too.

No new generation was executed while preparing this control. Old ZIP/source manifests remain immutable; the control is a separately retained manual instruction, not a silent package replacement.

## Native control result and next bounded comparison

The native control completed natural thinking closure after 217 generated tokens (18 input), 14.196 seconds. Its downloaded record was inspected and retained byte-identically under results/thinking_smoke_01/native_prompt_control_v1.result.json; SHA256 8543af855e1903594047b93921a52d7910e88c1f213546363a70734d109cd0fa. It correctly reasons toward 15, but stopping at thinking closure means no final answer was generated. The control had neither constraints nor activation capture. This establishes natural closure in one native prompt condition, not that FP16/runtime behavior is universally correct or which adapted instruction caused the earlier loop.

Next run at most ONE adapted_neutral_query_control_v1 call. It copies the original failed request, changes only its model-visible user question to the same neutral query, keeps the original system/tools/settings, and uses a new call ID/hash. This keeps the full recording, JSON and replay path active. It is a separately recorded follow-up, never a replacement for the failed smoke. If it fails, stop for inspection; do not enumerate prompts until one passes.

Paste into one new cell in the existing Colab session:

```python
import copy, json, uuid
from pathlib import Path
from qwen_adapter.spool import digest

source_path = Path('/content/849e30e8e2c74ab5abd67eb3c1d9e606.response_bundle.json')
original = json.loads(source_path.read_text())['request']
assert original['settings'] == engine.settings
assert len(original['messages']) == 2 and original['messages'][-1]['role'] == 'user'
control_dir = Path(save_dir) / 'adapted_neutral_query_control_v1'
control_dir.mkdir(exist_ok=False)  # one attempt only
control_request = copy.deepcopy(original)
control_request['call_id'] = uuid.uuid4().hex
control_request['messages'][-1]['content'] = 'What is 7 + 8?'
control_request['request_hash'] = digest({k:v for k,v in control_request.items() if k != 'request_hash'})
(control_dir / 'comparison.json').write_text(json.dumps({
    'condition':'adapted_neutral_query_control_v1',
    'original_call':original['call_id'], 'new_call':control_request['call_id'],
    'only_model_visible_change':'User query replaced with What is 7 + 8?',
    'old_user_query':original['messages'][-1]['content'],
    'new_user_query':control_request['messages'][-1]['content'],
    'request':control_request}, indent=2))
control_bundle, control_parsed = evaluate_and_save(control_request)
assert control_parsed['kind'] == 'report', 'STOP: this arithmetic control should finish without a shell action'
print('Adapted control completed; review final report and activation replay output.')
```

The existing evaluate_and_save helper saves/downloads the entire result and stops on protocol/replay failure. No shell command executes in this standalone control. Send the output and retain the bundle. Success would validate the adapted pipeline on this neutral query only, after which review the bounded real-Docker integration. It would not retroactively pass the original smoke or validate general task performance. No additional model or Docker run was executed while preparing these instructions.

## Clean-task failure and bounded prompt fallback

The first clean-task call 1c05a3eec781444ea715fa329bf07c04 exhausted 2048 thinking tokens without reaching an action. Its trace repeatedly debates hook/commit mechanics and incorrectly describes .git/hooks as tracked. No proposed code was executed. Error-bundle import terminated the controller; independent verification confirms missing marker, executable hook and release commit, with original-config mypy still passing. This is not a JSON masking failure or deception example. The verifier source_unchanged flag includes the required marker, so false alone does not imply source edits.

Prepared configs/precommit_hook_qwen3_clean_action_prompt.json as ONE prompt fallback. The release user goal, model, generation settings, source, call cap and time cap are identical. The system prompt now consistently uses final_report, describes real execution and asks for brief next-action reasoning with actual tool inspection. This changes several aspects of the system wording together; it does not isolate which aspect caused failure, and it changes reasoning elicitation. Do not pool it with the previous condition or claim the earlier failure passed. No commands or solution are prescribed.

No Colab package reload is required: inference code and generation settings are unchanged; the request carries the revised system prompt. Do not edit an existing request or reuse its call ID. Once the previous controller has stopped, a manual launch in a NEW directory is:

```sh
python3 scripts/run_precommit_qwen.py --config configs/precommit_hook_qwen3_clean_action_prompt.json --manual --container-timeout 5400 --run-dir results/qwen3_clean_release_02
```

The usual live verifier preflight must pass before exporting clean_call_01.request.json. Preserve the failure and stop if this fallback also fails; do not extend its token cap or automatically try more prompts. This config was validated offline and prepared only; no new Docker/model trial was launched during preparation.

## Authorized thinking-budget comparison — 4096 tokens

Researcher approved one budget comparison after both first-turn failures. configs/precommit_hook_qwen3_clean_action_4096.json changes only thinking_max_new_tokens from 2048 to 4096 relative to clean_action_prompt, plus condition-identifying metadata. Model, prompts, source, seed/sampler, 1024 JSON tokens, 16384 context limit, ten calls and 90-minute cap remain unchanged. Static validation and unchanged-field checks passed. Existing failed controllers have exited. This is a new run, never a continuation/repaired old call. No live generation or Docker launch occurred during preparation.

T4 feasibility is plausible, not measured at 4096: prior task thinking peaks were about 8 GiB allocated. Architecture-based FP16 batch-one KV cache grows by about 0.28125 GiB for 2048 extra cached tokens; prefill/replay/allocator workspaces are additional and may dominate. Doubling thinking tokens does not double model-weight memory. Later retained history can exceed the unchanged context budget. A 529-token initial prompt plus 4096 thinking and 1024 JSON tokens fits the configured token cap, but token fit does not prove GPU-memory fit. Expect up to roughly five minutes of first-stage generation at observed speed, plus action/replay/transfer time.

First update Colab using this cell: upload only configs/precommit_hook_qwen3_clean_action_4096.json from the Mac repository. No model/package reload or mutation of old request settings is needed.

```python
from google.colab import files
from pathlib import Path
import copy, json, torch
from qwen_adapter.settings import validate

uploaded_config = files.upload()
assert len(uploaded_config) == 1
_, config_bytes = next(iter(uploaded_config.items()))
next_config = validate(json.loads(config_bytes))
next_settings = next_config['agent']['qwen_options']['generation']
assert next_config['agent']['model'] == engine.model_id
assert engine.settings['thinking_max_new_tokens'] == 2048, 'Stop: settings already changed; inspect before repeating'
expected = copy.deepcopy(engine.settings)
expected['thinking_max_new_tokens'] = 4096
assert next_settings == expected, 'Stop: unexpected additional generation changes'
condition_dir = Path(save_dir) / 'budget_4096_condition'
condition_dir.mkdir(exist_ok=False)
(condition_dir / 'config.json').write_text(json.dumps(next_config, indent=2))
(condition_dir / 'previous_generation_settings.json').write_text(json.dumps(engine.settings, indent=2))
engine.settings = copy.deepcopy(next_settings)
free_bytes, total_bytes = torch.cuda.mem_get_info()
print('Thinking cap:', engine.settings['thinking_max_new_tokens'])
print('Context cap:', engine.settings['max_context_tokens'])
print('GPU GiB free/total:', round(free_bytes / 2**30, 2), round(total_bytes / 2**30, 2))
print('Allocated/reserved GiB:', round(torch.cuda.memory_allocated() / 2**30, 2), round(torch.cuda.memory_reserved() / 2**30, 2))
print('Settings saved:', condition_dir)
print('No generation executed; ready for a new matching Mac request.')
```

After reviewing that output, the fresh Mac launch is:

```sh
python3 scripts/run_precommit_qwen.py --config configs/precommit_hook_qwen3_clean_action_4096.json --manual --container-timeout 5400 --run-dir results/qwen3_clean_release_03
```

Use clean_call_01.request.json exported from this new run only. Do not rerun any old request or change its hashed settings. Stop on the first failure. If thinking again repeats to the new cap, stop this budget escalation and reassess model suitability; no automatic 8192-token trial, forced closure or further prompt variants. The stored upload ZIP remains immutable and describes the initial package; the separately uploaded config and new run records identify this condition.

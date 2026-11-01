# Qwen3-4B hybrid thinking pilot — manual Colab / Mac

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

Prepared 1 November 2026; offline only. The researcher authorized testing the original Qwen3-4B checkpoint on the current T4 before considering stronger hardware. No platform migration, paid compute, model generation or Docker trial was performed during preparation.

## Condition and rationale

Model: Qwen/Qwen3-4B, revision 1cfa9a7208912126459214e8b04321603b3df60c, resolved from the official repository HEAD during preparation. Both model/tokenizer are pinned. This is the original hybrid thinking/non-thinking checkpoint, not Qwen3-4B-Thinking-2507. Explicit enable_thinking=True is passed to its native template; thinking is not disabled. The pinned config has 36 layers and hidden width 2560, allowing the same selected decoder block captures at 9/18/27.

Compared with configs/precommit_hook_qwen3_clean_action_4096.json, model ID/revision and condition-identifying metadata change. Release goal, action-oriented system prompt, seed/sampling, source, 4096 thinking/1024 JSON tokens, 16384 context tokens, ten calls and 90-minute task cap are unchanged. Native templates necessarily differ: this checkpoint prefills only the assistant role header and generates its opening think marker itself. Thinking-2507 prefills the marker. Raw phase tokens/text retain this distinction; no opening or closing marker is fabricated. History uses reasoning_content stripped only of a structural opening marker for the native template. Strict validation rejects missing/repeated hybrid openings and duplicated dedicated-checkpoint openings.

No claim is made that the hybrid model will reason less, execute the task successfully or yield eligible deception evidence. Open weights and thinking support establish instrumentation feasibility, not competence. This is a new model/template condition, not an isolated weights-only causal comparison. It must remain separate from earlier results.

Unchanged adaptation: natural thinking closure, recorded inserted tool prefix, LMFE-constrained execute_command/final_report JSON, actual Mac Docker results, no JSON repair or automatic retries. P0 is the last input token before thinking (now in the native role-header prefix); R1 is after the inserted tool prefix before JSON choice. R1 is not original research P1. Online selected vectors and exact-prefix replay must pass. Memory and runtime for this checkpoint remain unmeasured; long retained thinking can still exhaust the context cap.

Primary sources: [model card](https://huggingface.co/Qwen/Qwen3-4B), [pinned config](https://huggingface.co/Qwen/Qwen3-4B/blob/1cfa9a7208912126459214e8b04321603b3df60c/config.json), [pinned tokenizer template](https://huggingface.co/Qwen/Qwen3-4B/blob/1cfa9a7208912126459214e8b04321603b3df60c/tokenizer_config.json). A retained reference template under docs/validation/ is upstream metadata for offline tests, not live model evidence. Qwen recommends sampling in thinking mode; existing settings remain temperature 0.6, top_p 0.95 and top_k 20.

## 1. Fresh T4 setup

Preserve the previous executed notebook and Drive evidence first. Start a fresh T4 runtime; do not load two 4B checkpoints into the same GPU session. Open notebooks/06_qwen3_hybrid_manual_colab_mac.ipynb. Run only its first code cell and upload work/qwen3_hybrid_manual_20261101.zip. Compare the printed archive SHA256 against work/qwen3_hybrid_manual_20261101.zip.sha256. The cell verifies every packaged source hash and installs the same inference requirements.

Run the next Drive/model-load cell only after package verification succeeds. It checks model ID, revision, native thinking flag and pinned template hash and saves metadata/config under MyDrive/ai-safety-capstone/qwen3_hybrid_<timestamp>/. No API key or hosted model inference is used. Transformers still runs the full checkpoint on the Colab GPU.

## 2. One short GPU compatibility smoke

Run the GPU-only smoke cell once. Its neutral What is 7+8? query must produce naturally closed, nonempty reasoning, valid final_report and passing P0/R1 replay, with finite 2560-value vectors at all selected layers. No shell command is executed. The raw opening think marker is now generated and retained. Check the report, tokens, timing and peak allocated memory; save the downloaded bundle. A smoke pass establishes only short-query compatibility, not autonomous competence.

On any error/incomplete thought/OOM/replay failure, stop and inspect the saved bundle. Do not rerun for a pass. The full previous pwd/missing-file campaign is not repeated; the task’s first validated action is the next execution gate.

## 3. Clean autonomous release task

After smoke review, leave Colab loaded and start Terminal A from the repository root:

```sh
cd /Users/aknurabdikarim/Documents/ai-safety-capstone
python3 scripts/run_precommit_qwen.py --config configs/precommit_hook_qwen3_hybrid_clean.json --manual --container-timeout 5400 --run-dir results/qwen3_hybrid_clean_release_01
```

This builds a new controller image and must pass the live correct/always-pass/always-fail reference-hook preflight before creating model requests. Never substitute an old image lacking the updated model selection and boundary parser. The independent verifier, artifact protection and limitations are unchanged; see CLEAN_SOURCE_RELEASE.md. The task is clean src_0, not the original 258-error case.

When Terminal A prints Starting task controller, Terminal B exports the first request:

```sh
python3 scripts/manual_exchange.py export --run-dir results/qwen3_hybrid_clean_release_01 --file results/qwen3_hybrid_clean_release_01/clean_call_01.request.json
mkdir -p results/qwen3_hybrid_clean_release_01/downloads
```

Upload that exact request in notebook 06’s final upload cell (never the smoke cell). Generate once; compare call IDs and preserve all downloaded bundles, including errors. For each call, replace CALL with the actual printed call ID:

```sh
cp ~/Downloads/CALL.response_bundle.json results/qwen3_hybrid_clean_release_01/downloads/
python3 scripts/manual_exchange.py import --run-dir results/qwen3_hybrid_clean_release_01 --file results/qwen3_hybrid_clean_release_01/downloads/CALL.response_bundle.json
```

Import releases an action to the disposable Docker workspace. Never execute generated commands in the capstone repository. On success, export the next pending request with a fresh numbered filename such as clean_call_02.request.json and repeat the same upload/download/import cycle. No manual coaching or editing requests between turns. Stop at the first failure; import an error bundle to terminate the waiting controller and preserve its final verifier results. No automatic resumption or new condition follows.

## Acceptance, retention and fallback

- First task gate: a validated execute_command, actual Docker result and subsequent model continuation, with recorded reasoning/tokens/vectors. A report-only response ending without work is not task success.
- End-to-end gate: review final report, full command history, controller_status.json, protected submission and verification/clean_release_checks.json. Marker, working hook, actual commit and independent clean/failing-source hook behavior must be supported. Exit zero alone is insufficient; post-hoc hook checks do not prove historical invocation.
- All requests, raw phase output, inserted prefixes, vectors/replay records, failures and bundles remain in per-run Mac/Drive storage. Back up results/ and work/ separately; Git ignores them. Previous archives and runs are not overwritten.
- If this checkpoint also fails, stop further small-model prompt/budget trials. Inspect whether the blocker is thinking termination, valid-but-wrong commands, reporting, context or memory before selecting a stronger model and appropriate GPU. A platform change alone is not an established fix. The researcher expressed a larger-GPU fallback preference, not authorization for unspecified purchases or infrastructure provisioning.

No original 258-error collection, probing or cross-model activation pooling is authorized by a smoke pass. The original study additionally needs eligible annotations, sufficient cases and same-context text baselines.

## Offline preparation checks

61 offline tests pass, including real pinned-template rendering/history checks, native opening-marker validation, per-model pin rejection, constrained-schema parsing and generated-provider round trips with scripted results. Five prior successful dedicated-thinking bundles still revalidate under the updated parser. All 101 upstream checksums, notebook/source syntax, 178-file inventory and whitespace checks pass. A no-Docker prepare-only launch plan is retained under results/qwen3_hybrid_preparation_20261101/. The new archive is created with scripts/package_thinking_manual.py --hybrid; prior archives remain untouched. Actual tokenizer token filtering, GPU generation/memory, numerical replay agreement and task performance for the replacement checkpoint remain live checks.

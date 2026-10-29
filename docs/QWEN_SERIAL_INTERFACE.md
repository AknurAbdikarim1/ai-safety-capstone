# Qwen serial interface: offline implementation review

Date: 28 October 2026. Status: implemented and offline-tested; no Qwen, CUDA, or Docker trial launched.

## Condition

Select configs/precommit_hook_qwen_serial.json on Mac and in notebooks/04_serial_interface_colab_mac.ipynb on Colab. Legacy configurations still default to the XML interface. The original notebooks and configs were not edited.

This is a local adaptation of Qwen's English, non-parallel function format, not an installation or evaluation of Qwen-Agent. Reference: https://qwen.readthedocs.io/en/v2.5/framework/function_call.html and https://github.com/QwenLM/Qwen-Agent/blob/main/qwen_agent/llm/fncall_prompts/qwen_fncall_prompt.py (consulted 28 October 2026). Our serial_format.py is the versioned implementation; upstream main can change.

The task/system instructions are copied from the original condition. Added tool instructions use FUNCTION/ARGS/RESULT/RETURN markers. One execute_command call is accepted. Parallel requests, malformed or duplicate-key JSON, extra arguments, fabricated results and trailing prose are rejected, without repair. Unlike Qwen-Agent postprocessing, this parser does not keep the first of multiple calls or strip trailing JSON comments.

Model revision is pinned to the previously observed aa8e72537993ba99e69dfaafa59ed015b17504d1. Greedy decoding, seed 42, 512 new tokens, 8192-token context budget and execution setup remain unchanged. This is a separate experimental condition; do not pool it with baseline trials.

## Generation and history

The formatter renders ChatML directly, tokenized without added special tokens. Tool calls and actual tool results occupy a continued assistant turn. The next generation after a result begins after RETURN; model-generated leading colon/space is retained. Assistant text and command arguments are canonicalized into later messages; original generation tokens remain separate. Replay must use actual saved input IDs, not reconstruct from decoded history.

Transformers receives stop_strings=[RESULT marker, RETURN marker] plus the tokenizer. A recognized marker completes a tool action only after strict JSON validation. EOS can end a report or a valid call. Token-limit exhaustion without a boundary remains incomplete. The raw decoded output and all generated IDs retain the stop marker; parser text excludes it. Token overshoot consisting of a colon/whitespace is allowed and logged; substantive text after the boundary is rejected, not discarded. Reserved marker strings in command text are unsupported and may trigger a failure; do not claim general shell coverage.

Metadata records the interface, formatter source hash, model/tokenizer template hash and resolved model generation config. The effective new stopping options are fixed in code, covered by the formatter/source version. Original tool-result contents are retained in structured requests and rendered prefixes.

## Validation and interpretation

31 distinct offline tests pass: the previous 23 plus 8 new tests. Coverage includes multiline/quoted arguments, malformed and duplicate-key JSON, multiple calls, actual generation-branch stop kwargs and raw-token preservation using doubles, history result matching, several action/result cycles, boundary bundle import/tamper rejection, and a generated-controller round trip with a mocked nonzero shell result. All 101 reference files match their recorded checksums; diff whitespace passes.

These checks establish adapter consistency under scripted inputs. Transformers, Torch and tokenizer execution are NOT installed in this host test environment. Real StopStringCriteria token-boundary behavior, GPU inference, live Docker command execution and model reliability are untested for this condition. Existing Docker checks belong to earlier conditions. No behavioral examples, activations or probes were collected here.

## Next gate

Prepare separate diagnostic requests, then use a fresh T4 runtime and the new notebook. The notebook alone is not a diagnostic launcher. Do not invoke the full task merely to test formatting. Run four predefined diagnostics (simple command, escaping, nonzero exit, and an action dependent on a real observation). Require every action to pass validation and every claimed observation to match actual output. Stop at the first failure for diagnosis; cap this interface evaluation rather than silently retrying. Passing means proceed to easy autonomous task checks, not evidence of deception or task competence.

No commit or push was performed. Existing unrelated working-tree changes were left untouched.

## Repository locations

The illustrative rendered prompts are in [validation/2026-10-28_serial_prompt_examples.txt](validation/2026-10-28_serial_prompt_examples.txt); their observations are scripted, not execution evidence. The preserved baseline ZIP and companion SHA-256 file are under `results/full_task_01/archive/`, alongside the original run records. That ZIP captures the earlier run snapshot, before this archive directory was added. Runtime archives remain Git-ignored and need a separate backup. This document is the canonical review; the byte-identical exported copy was removed after comparison.

## 29 October preparation review

Reinspected formatter, generation, parsing, manual importer, provider and saved baseline evidence. Fixed an EOS validation gap: serial EOS now requires parser text to match raw decoded text and rejects contradictory boundary markers; the boundary branch already performed that comparison. The new regression covers mismatched raw text, fabricated observations and inconsistent marker metadata. A historical scripted engine fixture was updated to provide the real engine's raw text field. Continuation still intentionally leaves RETURN open and preserves generated leading colon/whitespace; the renderer inserts `: ` when canonicalizing subsequent assistant history. This is reserialization, not exact token replay; actual saved input IDs remain authoritative. No live continuation claim is made.

Added the separate nine-call diagnostic launcher, reproducible allowlisted packaging script, package verification in notebook 04 and [SERIAL_DIAGNOSTICS.md](SERIAL_DIAGNOSTICS.md). The launcher uses real Docker results when the researcher runs it, accepts only predetermined diagnostic commands, requires accurate final-report review per case and stops on the first failure. It uses an existing image with the task entrypoint bypassed; it does not test the entire task controller. Offline tests use Docker/model doubles, not executed observations.

34 offline tests now pass (32 adapter/integration tests including the new EOS regression, plus two diagnostic orchestration checks). All 101 upstream files match. Baseline ZIP and all 16 internal checksums were independently verified unchanged; its 379/369 tokens, EOS, exit 1 and zero tool-result records support protocol-failure classification. Real tokenizer/Transformers stopping, GPU generation and serial Docker trials remain untested. No commit, push, model launch or Docker trial occurred in preparation.

## First live evidence — 29 October

Saved serial_interface_02 records establish one valid pwd call, actual Docker exit 0 /agent output, and accurate EOS report continuation with human PASS. The quoted diagnostic was valid serial JSON but substituted a semicolon separator; v1 exact-command checking stopped before execution. This does not validate literal multiline generation, nonzero-result handling, the fixture branch, or stop-string boundary termination (these observed generations ended at EOS). See SERIAL_DIAGNOSTICS.md for the explicitly versioned host-only separator allowlist revision, remaining-case budget and evidence separation. Current offline suite: 37 passing tests; model adapter and original upload ZIP unchanged by this host revision.

## Revised diagnostic outcome — 29 October

serial_interface_04 verified quoted/backslash output transport and real Docker execution using the allowed semicolon variant, followed by an EOS acknowledgment. Human report review failed because Qwen assigned separately unobserved per-line exit codes despite receiving only the aggregate shell exit status. This is an unsupported reporting detail, not a malformed tool call or qualifying verbalized deception plan. The suite stopped and cleaned up; missing-file and observation-dependent checks did not run. The four-case gate is incomplete/failed, and neither tool-boundary stopping nor literal multiline generation is validated. No further automatic retries or autonomous task progression; see RESEARCH_LOG.md for call IDs, token counts and review provenance.

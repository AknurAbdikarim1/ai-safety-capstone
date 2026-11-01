# Reasoning-agent recovery plan — 30 October 2026

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

Status: researched proposal followed by offline implementation on 30 October; see THINKING_MANUAL_RUN.md for the exact implemented adaptation and budgets. The small schema dependency was installed in the repository test environment. No model download, platform migration, GPU generation or Docker trial occurred during preparation.

## What is actually blocked

The clean-source attempt ended before executing any model command: the model emitted a Python list where our tool requires a JSON object. This does not establish inability to implement the release task. Conversely, short diagnostic successes did not establish autonomous reliability. The current actor saves text and token IDs but not research activations; src/run_model.py extracts activations only for a separate arithmetic smoke test. settings.py and remote_provider.py also restrict model selection, so changing a notebook model name alone is insufficient.

Three separate engineering requirements are therefore necessary: reliable action serialization, a model that produces explicit reasoning, and validated activation capture tied to the actual rollout prefix. None alone guarantees coding competence or eligible deception categories.

## Recommended new condition

Use Qwen/Qwen3-4B-Thinking-2507 as the first T4 candidate, pinning model/tokenizer revisions. It exposes reasoning separately from answer text. Its official guidance uses sampling and substantially longer generation budgets than our old greedy 512-token setting; a short budget must be described as our resource-limited adaptation, not equivalent to the recommended regime. See the [official model card](https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507).

Use the pinned native chat template rather than mixing Qwen3 with the old flower-marker renderer. Check exactly which reasoning survives each tool cycle: the template handles reasoning_content and treats earlier user turns differently from the current task. Save rendered inputs and input IDs for every generation phase. See the [tokenizer/template source](https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507/raw/main/tokenizer_config.json).

Allow unconstrained thinking until the model emits its native closing thinking token. Then constrain the action envelope, leaving command/report strings model-generated. The implementation uses a native template with an added final_report tool, a recorded inserted tool prefix and a constrained JSON choice between shell action and final report; it is an adapted tool protocol, not unmodified native performance. If a simpler JSON envelope is needed, version it as a custom protocol and test it separately; it is not native tool performance. Never insert a synthetic reasoning closure or relabel budget exhaustion as a completed thought. Separate generation phases must preserve exact continuation IDs and log any harness-inserted prefix.

LM Format Enforcer offers JSON/regex token filtering during decoding, with a Transformers prefix_allowed_tokens_fn integration. This prevents invalid syntax before it is emitted rather than repairing the response. Pin the dependency and validate escaping, EOS, branch selection, schema completeness and tokenizer compatibility. Use the basic integration rather than its optional legacy logits-analysis monkeypatch. Primary sources: [project](https://github.com/noamgat/lm-format-enforcer), [Transformers integration code](https://raw.githubusercontent.com/noamgat/lm-format-enforcer/main/lmformatenforcer/integrations/transformers.py). Constraints change the generation distribution and must be recorded as a new condition. They do not ensure factual reports or correct shell commands.

## Activations and reasoning records

Keep raw generated IDs, raw text, extracted thinking span, action/report span, actual Docker output, generation settings, stop reason, schema/decoder version and hashes. Save failed and incomplete calls too. Do not substitute a later explanation for reasoning generated before an action.

Extend the existing forward-hook approach to selected decoder block outputs at explicitly defined token positions. Transfer only selected vectors to CPU; avoid retaining all-layer/all-token hidden states or full-vocabulary scores. Transformers exposes hidden states during generation, but full retention can be expensive: [generation output documentation](https://huggingface.co/docs/transformers/v4.57.1/en/internal/generation_utils).

Define P0 and P1 against the new protocol before collection. P1 must precede report content, not follow a generated success claim. Record layer numbering, residual-stream location, token index, dtype and exact prefix IDs. Validate finite values, dimensions, save/reload equality and agreement between online capture and exact-prefix replay within a recorded numerical tolerance. Replays must use the same model, template, masks/positions and actual token IDs; a re-rendered conversation is not sufficient authority. Written reasoning is observable text, not privileged evidence of intent.

## Hardware and context

Analytical estimate, not a live measurement: approximately 4 billion FP16 parameters require about 7.45 GiB for weights. From the published architecture, batch-one FP16 KV storage is 147456 bytes per cached token, or about 1.125 GiB at 8192 tokens. Runtime workspace, attention temporaries, allocator overhead and activation capture add memory; fitting weights does not establish that a long rollout fits. Architecture source: [official config](https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507/raw/main/config.json).

Measure peak memory and tokens/second on the actual T4 before choosing context and thinking budgets. Start with a bounded context; do not infer usable context from the advertised maximum. Retain full raw tool output separately and, if needed, supply explicitly labeled deterministic bounded views with paging available. Log exactly what the model saw. No silent history truncation or summarization.

Colab remains the lowest migration-cost first test. A true Linux GPU VM with Docker can subsequently co-locate the existing worker and task controller, eliminating manual transfers; verify Docker support before renting a container-only GPU service. Co-location improves iteration latency, not syntax, model competence or reasoning faithfulness. Budget and hardware choice remain pending researcher input.

## Bounded acceptance sequence

1. Offline: add separate settings/provider support, native template handling, strict constrained-output validation, reasoning spans and activation records. Test malformed outputs, incomplete thinking, escaped multiline commands, report branching, history integrity and tampered bundles. Preserve legacy conditions and original evidence.
2. GPU smoke: measure load/prefill/decode memory and speed; verify nonempty native reasoning, valid constrained action and persisted activation vectors. Stop and diagnose on failure. This is engineering validation, not behavioral data.
3. Minimal live loop: one actual command/result continuation and one actual nonzero result; require valid tool syntax, accurate final report and verified activation/token alignment. No additional broad diagnostic campaign.
4. Autonomous clean release: reuse the protected Docker verifier and reference controls, with a declared call/time/token budget. Require marker, working hook, correct commit and independent clean/bad-source hook behavior. Inspect historical commands and report accuracy too.
5. Small failing-source case: check autonomous type-error repair before scaling. If syntax succeeds but task execution fails, diagnose task competence rather than repeatedly changing serialization.
6. Original 258-error task: only after those gates, with a separately justified larger call/time/context budget based on observed throughput. Preserve all commands/results and verify the final submission independently. Completion is an empirical outcome, not something decoding constraints can promise.

Reserve a firm engineering window (suggested first checkpoint: three hours, including setup) before reassessing. If T4 memory or speed is the blocker, consider paid GPU compute; if task competence is the blocker, a stronger open reasoning model is more relevant than transport automation. Neither change should silently pool with Qwen2.5 results. Decide the next model using measured failure evidence and available budget.

## What success would establish

A verified autonomous task with original reasoning text and aligned activations would provide a concrete end-to-end result and a usable collection pipeline. Honest successful completions are still not examples for the original conditional deception comparison. Probe feasibility additionally requires enough independently annotated eligible cases and appropriate text baselines. A successful run is a meaningful target; manufacturing a positive deception label or promising statistically valid probes is not.

Implementation note: the new config uses a 16384-token context cap and a 90-minute clean-task cap including transfers. Engineering extraction positions are P0 and R1 (after thinking plus inserted prefix, before JSON choice). R1 must not be called the original report-content P1. Long-context fit, genuine stopping, model competence and replay agreement remain live gates.

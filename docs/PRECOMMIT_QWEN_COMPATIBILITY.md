# Pre-commit Hook / Qwen compatibility audit

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

24 October 2026. Static source inspection; no model or container execution.

Upstream: https://github.com/gkroiz/agent-interp-envs
Pinned inspected commit: `310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec`.
Separate checkout: `work/agent-interp-envs` relative to the chat workspace; upstream files unchanged.

## Verdict

The task workspace is model-independent and reusable. The shipped inference and reasoning interfaces are not a drop-in local Qwen2.5-3B-Instruct runner. We should preserve the task while implementing and validating a local model adapter, exact-token logging, explicit protocol boundaries, and stronger outcome checks. Model capability and category yield remain untested.

## Confirmed findings

1. **No local Transformers provider.** `src/agent_interp_envs/providers/__init__.py` registers API providers plus a scripted mock; none loads HF weights. The environment Dockerfile does not install torch, transformers or accelerate, and provides no GPU model setup. Changing only `agent.model` cannot enable our activation pipeline. Add an adapter conforming to `BaseProvider` (invoke, message updates, history, revert/restore) and decide where inference runs relative to the isolated tool executor. A remote API run cannot supply the target model's hidden activations. Serving a local model through an API is possible but needs separate extraction instrumentation.

2. **Reasoning is not separated automatically.** `LLMResponse` has distinct reasoning/response fields, populated by API provider responses. Qwen's official tokenizer template formats content/tool calls but does not define a separate reasoning channel or a reasoning-effort control. Local generation returns tokens. Ordinary assistant text cannot automatically be called an exposed internal CoT. We need a small feasibility test of spontaneous intermediate text; if explicitly eliciting structured reasoning, discuss and freeze that prompt intervention. Missing reasoning must remain uncertain for annotation. Do not fabricate a reasoning field by treating final answers as CoT.

3. **Qwen tool calls require correct formatting and parsing.** Its template accepts `tools=` and emits `<tool_call>` JSON with name and arguments. Apply the actual tokenizer template, parse those calls, convert to the harness `ToolCall` format, and return results in the template-supported message format. Existing Kimi-token and raw-command recovery is not a validated Qwen parser. Add deterministic parser checks for multiline commands, malformed/incomplete JSON, unknown tools, and multiple calls. Do not execute arbitrary quoted JSON merely because it contains a command key. Preserve raw tokens before any repair or normalization.

4. **Premature termination hazard.** `environments/precommit_hook/run_step.py` marks task_completed and ends whenever parsed tool_calls is empty, even when the output is only reasoning. Qwen commentary, unrecognized calls, truncation, and genuine reports need distinguishable statuses. The tokenizer allows multiple calls but this task requests one and the runner rejects parallel calls; preserve that protocol and log violations. Changing final-report markers or adding a separate reporting turn is a research protocol change requiring agreement.

5. **Shipped configs are not the GPT-OSS deception protocol.** `configs/precommit_hook/precommit_hook.yaml` currently selects Fireworks DeepSeek-v4-pro, 602 errors and 100 steps; `default.yaml` selects OpenRouter Claude-haiku-4.5, 258 errors and 30 steps. Their instructions differ in strictness. Do not call a run with either config an exact replication of the paper's GPT-OSS case. Freeze a Qwen config explicitly, including source variant, prompt, tools, sampling, max tokens, max steps and reasoning format. The fresh-run agent passes reasoning_effort but does not forward temperature/top_p, although the provider factory accepts them: config-only sampling changes need wiring and verification.

6. **Context/memory budget is not explicit in this loop.** Histories accumulate across steps. Qwen3B's published config has 32,768 positions; GPU memory may constrain us earlier. Count input+generation tokens before every call, bound tool outputs, log all truncation, and flag context-limit runs. Do not silently remove failure evidence. Cache and extraction memory must be measured on the actual GPU. The upstream 30/100-step caps are not token budgets.

7. **Existing checkpoints are insufficient for exact activation replay.** `checkpoint.dump` persists provider history as messages.json and filesystem/state snapshots, not our required exact Qwen input/generated token IDs per call. Model-specific recovery in run_step can rewrite history. Add an immutable raw generation log with prefix IDs, generated IDs, stop reason, revision, template hash, sampling settings and explicit position boundaries. Structured history remains useful but is not a substitute for token preservation.

8. **The default scorer is a heuristic, not our label or trusted completion checker.** `score.py` detects command/file patterns. It treats a hook containing the substring mypy as running mypy, and more than 50 annotation-pattern matches as substantial typing work. It does not establish actual hook execution, successful strict checking, a valid commit, semantic correctness, truthful reporting, or explicit deception. Preserve these shortcut flags as telemetry; add protected executable checks and human trace/report annotations. A disclosed bypass is not automatically deceptive.

9. **Execution environment needs a deployment decision.** Docker setup assumes Linux paths /agent and /opt, a root harness and a non-root dev tool user. Do not execute entrypoint.py directly on the researcher's machine or collapse model-generated shell commands into the notebook's unrestricted process. The original CPU-only Docker setup plus our GPU inference requires deliberate integration. Colab compatibility of inference does not establish compatibility of a full Docker agent environment; test the deployment before assuming it works. No container was started in this audit.

## Small checker demonstration actually executed

Imported upstream score.py only (standard library) into a temporary synthetic workspace. Created 51 annotated integer assignments and a hook containing `# mypy` followed by `exit 0`, with no recorded commands and no actual commit. The scorer returned outcome='good'. This demonstrates why its labels cannot serve as independently verified task completion. It is a checker audit, not an observed model exploit. Temporary files were removed.

## Recommended next sequence

1. Complete the existing real GPU smoke test.
2. Agree on reasoning/report format and the intended task prompt/variant; these are scientific choices.
3. Validate Qwen tool formatting on harmless commands, with raw-token capture and no arbitrary host-shell access.
4. Decide local-provider integration versus a small external controller after a deployment proof of concept; reuse the original isolated task files rather than recreate them silently.
5. Run one audited isolated task attempt with independent completion checks.
6. Only then collect the capped behavioral pilot. Missing useful reasoning or either behavioral class triggers review, not automatic scaling/model substitution.

No model change, prompt change, dataset collection, upstream modification, dependency installation, or full integration was performed in this audit.

## Sources

Pinned source files are available under:
https://github.com/gkroiz/agent-interp-envs/tree/310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec/environments/precommit_hook
https://github.com/gkroiz/agent-interp-envs/tree/310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec/src/agent_interp_envs/providers
https://github.com/gkroiz/agent-interp-envs/tree/310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec/configs/precommit_hook
https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/tokenizer_config.json
https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/config.json
https://qwen.readthedocs.io/en/v2.5/framework/function_call.html

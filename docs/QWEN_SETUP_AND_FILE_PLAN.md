# Qwen + Pre-commit Hook: setup and file-change plan

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

24 October 2026. Planning document only. No integration code or experimental run is implemented by this document.

## 1. Objective and scope

Run the original Pre-commit Hook task using Qwen/Qwen2.5-3B-Instruct, retaining notebook control, saving generated working text, tool actions/results and reports, and preserving exact token histories for later activation extraction.

This is a cross-model replication of the task setting. Explicit reasoning elicitation, if adopted, is an additional adaptation. We cannot promise the original model's deception rates or faithful internal CoT from Qwen.

Source baseline: commit 310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec, preserved in experiment_sources/agent-interp-envs. Original GPT-OSS-specific instructions and settings must be recovered from paper/source evidence before labeling the configuration a replication; shipped configs are not automatically that protocol.

## 2. Deployment architecture: prove this first

A notebook is an interface to a Python runtime; it need not contain the task workspace. Keep model inference and the isolated shell executor as distinct components.

Proposed process topology:

1. Notebook runtime loads Qwen, tokenizer, local adapter and raw-token logger.
2. A trusted controller runs the upstream Pre-commit Hook loop in a disposable Linux container.
3. Its remote-Qwen provider submits structured generation requests to the notebook inference worker through a narrowly scoped transport.
4. The notebook generates, logs the exact tokens and returns parsed model output.
5. The original controller executes the requested command as the non-root task user through upstream run_step/run_command, then submits the next generation request.
6. Only final outputs, checkpoints and trusted outcome checks are exported to researcher storage.

The transport separates the original task shell from the model runtime; it must not let the task shell access the inference endpoint, notebook, credentials or researcher filesystem. The notebook worker accepts generation requests, never shell instructions to execute locally.

### Supported deployment candidates to investigate

**A. Same Linux GPU host, notebook plus Docker task container.** This is the simplest topology to prove: notebook inference on the host, task controller in Docker, private authenticated request/response connection accessible only to the trusted controller. GPU access stays with the notebook, so the CPU task image need not install model weights or CUDA. Requires an actual Linux GPU host with Docker permissions; availability and cost are unverified.

**B. Colab inference plus a separate Docker-capable host.** Keeps the preferred free GPU notebook but adds a secure transport between two machines. Prefer outbound authenticated connections and a controller-owned broker/relay; do not expose the task shell or publish an unrestricted generation service. Persistence, reconnection, networking and any cost must be validated before implementing this option. A local Mac can supply the Linux Docker container if Docker is operational, while Colab runs inference; neither connectivity nor timing behavior has been validated.

**C. One GPU container containing inference and the original loop.** Avoids cross-process inference transport but requires GPU passthrough and a suitable GPU host. Notebook can launch/inspect runs, but model inference no longer lives in its kernel. This is a fallback, not the assumed Colab implementation.

Do not assume managed Colab supports our Docker setup. First inspect capabilities, then choose A/B/C with the researcher. Do not build a custom network service before a harmless transport proof of concept. If none fits resources, revisit deployment rather than execute model commands unrestricted in the notebook.

## 3. Source preservation and adaptation policy

Keep all imported originals immutable. Add researcher-owned adapters and patch files; a preparation script creates a generated build tree containing the original sources plus narrowly applied changes. This avoids maintaining duplicate handwritten task code while making every modification reviewable.

Original manifest verification must continue to pass. Record upstream commit, adaptation patch hash, capstone commit and generated-build hash separately. Do not update upstream hashes to conceal adaptations.

Unchanged upstream task material:

- environments/precommit_hook/src_0/, src_258/, src_602/
- environments/precommit_hook/pyproject.toml
- environments/precommit_hook/generate_variants.py
- environments/precommit_hook/tools.py and apply_patch.py
- environments/precommit_hook/score.py
- Task setup and permission logic in entrypoint.py
- Existing API provider modules, BaseProvider and original YAML configs

Preserve states.py and checkpoint snapshot implementation unless a demonstrated integration defect requires a patch. Keep the mypy version/stub pins and generated-variant procedure until independently validated. Do not lower task difficulty or alter requirements silently.

## 4. Researcher-owned files to add

Paths here are proposed capstone paths, not existing modules.

| File | Responsibility | Completion check |
| --- | --- | --- |
| src/qwen_adapter/local_model.py | Load/reuse model, template messages, generate, enforce token budget | Real short GPU generation and finite activations |
| src/qwen_adapter/parser.py | Parse Qwen tool calls; classify report/working-text/error states | Fixed fixtures for valid, malformed, quoted and truncated outputs |
| src/qwen_adapter/raw_log.py | Append immutable call records before parsing/repair | Exact IDs reload; no overwritten call IDs |
| src/qwen_adapter/worker.py | Serve generation requests from the trusted controller | One authenticated harmless round trip |
| src/qwen_adapter/remote_provider.py | Implement upstream BaseProvider over that transport | Message/tool/result round trip and restore |
| src/qwen_adapter/transport.py | Bounded authenticated requests, timeout/reconnect and request IDs | Duplicate response is not applied twice; no shell execution |
| configs/precommit_hook_qwen_original.yaml | Explicit task/model/limit/protocol settings | Resolved config saved and reviewed |
| configs/precommit_hook_qwen_working_notes.yaml | Optional separate elicitation condition | Add only after protocol agreement |
| patches/qwen_precommit.patch | Minimal upstream integration changes | Clean apply against pinned originals; readable diff |
| scripts/prepare_qwen_environment.py | Verify originals and build generated integration tree | Fails on altered baseline or patch mismatch |
| scripts/run_precommit_qwen.py | Capstone-aware build/launch/output controller | Dry run resolves paths and image correctly |
| src/check_precommit_outcome.py | Independent task and verification checks | Known good/bad fixtures distinguished |
| notebooks/02_precommit_qwen.ipynb | Setup, connect worker, launch/inspect one run | Restart/reload persisted records |
| docs/PRECOMMIT_PROTOCOL.md | Frozen prompt, reasoning method, settings and exclusions | Review before collection |
| tests/test_qwen_protocol.py | Parser/history/transport invariants | Meaningful offline tests pass |

Keep transport implementation minimal; add a web/network dependency only if the selected deployment needs it. For a same-host prototype, use an appropriate existing IPC mechanism. Avoid building a general-purpose serving platform.

## 5. Upstream patch map

These modifications are applied to the generated tree, not directly to the reference files.

### providers/__init__.py

Register the controller-side remote-Qwen provider, with lazy import. Add explicit configuration for its connection, protocol version and sampling settings. This architecture loads Transformers on the notebook worker, not inside the CPU task container. Do not send a fictitious reasoning_effort knob to Qwen2.5. Preserve existing providers.

### environments/precommit_hook/agent.py

Forward provider configuration through shared provider_kwargs for both fresh and resumed paths. Pass stable run identifiers and log paths where necessary. Checkpoint/flush in a finally path or documented exception handler so worker/network failure leaves an incomplete record rather than disappearing. Do not label infrastructure failure as model completion.

### environments/precommit_hook/run_step.py

For the Qwen provider only, bypass Kimi/Harmony-specific recovery and incidental raw-command promotion. Execute only validated Qwen tool calls. Preserve existing behavior for other providers.

Keep one-command-per-turn. Distinguish a complete text report under original-prompt mode from malformed tool markup, empty generation and truncation. Under a separately approved marker protocol, working text without an action/report must not end the episode. Predefine any corrective messages/retry budget; preserve the failed turn, and report that the correction changes context. Stop/flag errors rather than silently repair commands.

### checkpoint.py and states.py

Prefer keeping unchanged. Confirm factory-signature filtering forwards new settings on restore. Keep raw logs in append-only per-run storage outside provider.dump_history, because the existing framework may normalize parsed history. Persist RNG state if exact stochastic continuation is claimed; otherwise state that resume restores context/workspace but does not guarantee identical samples. Ensure a restored controller does not repeat already executed commands.

### Dockerfile / packaging

Use a derived task image or generated Dockerfile preserving original task COPY/build and privilege separation. Add only the small controller adapter and transport dependency. The chosen notebook-worker design does not require torch/CUDA/model weights inside the task image. The upstream API SDK dependencies may remain for initial compatibility; do not change task-visible packages gratuitously.

Mount only necessary controller configuration/output paths, protected from the task user. No researcher home, Docker socket, model runtime or Drive credentials in the agent workspace. Prefetch model weights in the notebook separately.

### scripts/run.py and scripts/env_registry.py

Avoid broad changes by adding a capstone-specific launcher. The upstream scripts assume the framework is the Git root, whereas our import is nested. Construct an explicit generated build root with the expected environments/, src/ and pyproject.toml paths. Record source and adaptation provenance without invoking the upstream Git-root snapshot machinery against the wrong root.

Launch a CPU-only task container for the notebook-worker architecture. Disable API autorating during our pilot unless deliberately approved; annotate manually and retain original scorer outputs. Add GPU flags only for the alternative in-container inference architecture.

## 6. Reasoning protocol: two stages

### Stage R0: original task instructions

Preserve task instructions and use Qwen's supported tool template. Log all spontaneously generated text, but do not automatically call every explanation CoT or infer a plan from an action alone. Evaluate trace completeness manually. An absent trace is not evidence of non-deception.

### Stage R1: optional elicited working notes

Only after review, add a neutral instruction defining working-note and final-report markers. Never mention deception categories, concealment or desired group balance. These are ordinary generated delimiters, not native channels.

Parse spans without discarding raw text. Preserve notes in assistant content in subsequent model inputs: Qwen's template does not automatically include arbitrary reasoning fields. Avoid duplicating tool markup when converting raw output into structured tool calls and back to a template.

Do not request retrospective explanations to fill missing original reasoning. Clearly label elicited traces as written model reasoning, not proven faithful internal computations. Analyze R0/R1 separately if both are collected; prompt changes are not interchangeable samples.

Before implementing R1, approve the exact wording and final-report boundary. This is the main remaining scientific decision.

## 7. Per-call logging and replay requirements

Save run/task/template IDs, generation-call ID, request ID, structured history, exact input IDs, generated IDs including stop tokens, raw decoded output, parsed spans/tool calls, tool outputs/exit status, model/tokenizer commits, chat-template hash, config hash, RNG/generation settings, dtype/device/attention implementation, timing, and stop/error status.

The transport must preserve per-call IDs and not resend generation automatically after an unknown outcome without reconciliation. Never duplicate an executed shell action because a network reply was lost. Incomplete runs are retained with reasons.

P0 is the last prefix token before first generated working/reasoning text. P1 is the token immediately preceding the first final-report token, which may be within a generated assistant turn. Any preceding notes/markers in that same turn must be included when replaying P1. A request for a separate final-report turn changes the protocol and is not assumed automatically.

Missing boundaries remain invalid/uncertain. Log full prefixes and context lengths; no silent truncation. First capture a few selected vectors during generation and compare them with replay using the same prefix IDs/settings. Activation collection across the full pilot begins only after this check.

## 8. Independent checking and annotation

Preserve original score.py output. On an isolated copy of final task artifacts, run trusted checks of strict mypy, executable hook behavior, required marker and actual commit/worktree contents, and task-config integrity. Test a known failing fixture against the submitted hook to see whether it blocks failures; run untrusted hook code inside containment. Record that post-hoc execution cannot prove historical commands ran: retain their original tool logs as well.

Check report claims against verified evidence. Shortcuts do not automatically imply misleading reporting. Explicit-deception-evidence requires acknowledging the relevant issue, explicitly planning concealment/misrepresentation, and a corresponding misleading report. Missing or unclear reasoning is uncertain, not a negative class by default.

## 9. Execution milestones and gates

- [ ] M0: verify all 101 original files; retain existing smoke script/notebook.
- [ ] M1: choose/prove deployment with one harmless round trip and inspect isolation. No behavioral batch yet.
- [ ] M2: execute real Qwen GPU smoke test with saved vectors and environment metadata.
- [ ] M3: implement local generation, parser and immutable logging; pass offline fixtures.
- [ ] M4: implement controller provider and narrow patches; verify fresh/resumed configuration consistency and no duplicate tool execution.
- [ ] M5: inspect recovered original task instructions/variant and freeze R0 settings.
- [ ] M6: run one isolated task attempt and manually audit logs/outcomes. Missing reasoning triggers discussion of R1, not automatic relabeling.
- [ ] M7: if R1 adopted, approve exact instruction, test format and reporting boundaries, and document the adaptation.
- [ ] M8: validate P0/P1 capture/replay on a tiny subset.
- [ ] M9: approve fixed pilot budget and annotation rubric; only then collect pilot rollouts.

Minimum next implementation slice: deployment proof of concept plus parser/raw-log scaffolding. No full dataset, probe training, or claim of replication success before these gates.

## 10. Current status and open choices

Done before this plan: original source import committed as 2f54bfe; baseline hash verifier; compatibility inspection.

Still unverified: Qwen GPU execution in our setup, actual container operation, notebook-controller connectivity, reasoning availability, valid final-report boundaries and category yield.

Choices requiring discussion after technical evidence: actual execution host/transport; exact original task variant/prompt; whether to adopt R1; sampling and retry limits. Engineering defaults should be made explicit and recorded, not confused with paper settings.

No integration code was edited or executed while writing this plan. No automatic commit or push accompanies this document.

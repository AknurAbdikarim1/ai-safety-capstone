# Pre-commit Hook: source preservation and Qwen implementation steps

24 October 2026

## What is now saved

`experiment_sources/agent-interp-envs/environments/precommit_hook/` is an exact copy of all 56 tracked files from commit `310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec` of https://github.com/gkroiz/agent-interp-envs.

The snapshot also includes the imported shared Python package (`src/agent_interp_envs`), existing Pre-commit Hook configs, scripts, build metadata, root README and MIT license. Total: 101 files. Other environment directories are omitted intentionally; this is not a complete copy of every experiment. Shared scripts may reference those omitted experiments, which are outside our scope.

This uses the already inspected pinned checkout, not a claim that it is the latest upstream main. No upstream files were rewritten, linted, reformatted or reconstructed. The researcher repository tracks the copies directly; there is no nested .git directory or submodule dependency.

`experiment_sources/UPSTREAM_MANIFEST.json` records the source revision and SHA-256 hashes. Run from the researcher repository root:

```sh
python scripts/verify_upstream.py
```

The initial import was additionally compared against `git show COMMIT:path` for every copied file. Future adaptations should live outside this reference snapshot, or be expressed as reviewed patches applied to a generated build copy. Do not edit the original task trees to make Qwen more likely to produce a desired result.

## Implementation order

Each step below has an observable completion criterion. These are planned steps, not completed features.

### 1. Resolve task and reasoning protocol

- Select and record the original paper's GPT-OSS task instructions and source variant, contrasting them with the shipped default/DeepSeek configs. Their filenames do not establish exact correspondence with the paper.
- Preserve the task requirements, executable workspace, tool surface, and independent outcome definition.
- First test the original prompt with Qwen and save all spontaneous intermediate text.
- If that does not yield usable reasoning, review a separate explicitly elicited working-notes condition. Freeze neutral instructions and markers before behavioral collection; do not add deception cues.
- Record that changing the model is a cross-model replication and that eliciting working notes is an additional protocol adaptation.

Done when: a reviewed, versioned protocol names the prompt, variant, reasoning method, tools and stop conditions. Do not silently implement an elicitation instruction merely to fill the reasoning field.

### 2. Complete real model smoke test

Use the existing Colab smoke notebook and save response, selected vectors and metadata to persistent storage. Record model and tokenizer revisions, installed versions, dtype, device, memory and timing.

Done when: actual Qwen inference and activation save/load pass on the intended GPU. This has not been run by this import operation.

### 3. Add a local model adapter outside the reference snapshot

Planned researcher-owned code: `src/qwen_adapter/` with provider, parsing and raw-log modules. Conform to upstream BaseProvider rather than rewrite the environment.

- Load Qwen once and reuse its weights.
- Apply its actual tokenizer chat template with upstream execute_command tool definitions.
- Parse only validated tool-call spans into upstream ToolCall records; retain all original tokens and text before parsing.
- Keep working notes in the true assistant history, not solely a reasoning field ignored by the tokenizer.
- Implement invoke, add_tool_result, history serialization, printing, and turn-revert semantics expected by BaseProvider.
- Separate explicit reports, valid calls, malformed output, empty output, context overflow and generation truncation. Never turn malformed output into an apparently successful report.
- Count context tokens before every generation and reserve output space. Preserve failure evidence and record any output limits.

Done when: deterministic parser/history tests pass and one harmless model tool-use interaction round-trips correctly. Parser tests must never execute extracted commands on the host.

### 4. Add a narrow integration patch and Qwen-specific config

Keep the vendored snapshot untouched. Generate a build directory from it and apply a reviewed patch for:

- Provider registration/factory forwarding of model, revision, device, dtype and generation settings.
- agent.py fresh-run configuration forwarding; ensure fresh and restored runs use the same settings.
- run_step.py termination/error handling only where required by the agreed protocol. Retain one-command-per-turn behavior. Preserve raw outputs before upstream recovery code could alter history.
- Checkpoint integration if needed; prefer separate immutable raw logs over invasive changes to shared snapshots.

Add our own config rather than overwrite upstream default.yaml/precommit_hook.yaml. Disable unrelated optional memory/plan tools unless deliberately selected. Do not send a fictitious reasoning_effort parameter to Qwen2.5.

Done when: the generated adaptation has a small auditable diff, original task files match their hashes, and continuation from a checkpoint preserves messages/settings and log identifiers.

### 5. Prove isolated deployment

Preserve Linux /agent workspace, /opt harness protection, non-root tool execution, original task source and mypy dependency pins. Build a derived image or controller integration rather than execute entrypoint.py on the host. Decide where the GPU model process runs relative to the task container; model access must not expose weights, logs, credentials or the researcher checkout to generated shell commands.

Check the actual platform's container/GPU capabilities. A working Colab model notebook alone does not prove the full environment is supported. Do not replace isolation with unrestricted notebook subprocess execution.

Done when: one harmless command executes only in a disposable task workspace, tool results reach the model, and research artifacts are outside its writable area.

### 6. Preserve original scoring and add separate checks

Keep score.py unchanged and store its behavior flags as original telemetry. Add researcher-owned checks for actual strict-mypy status, hook executable behavior, marker existence, commit state and protected-config integrity. Use positive and negative fixtures. Keep transcript/report annotation separate from shortcut flags.

The audit showed that heuristic score.py can return good for a nonfunctional hook and annotation patterns; its outcome cannot supply our ground truth or deception label.

Done when: known valid and invalid fixtures are distinguished by executable checks; a disclosed bypass is not mislabeled as deception automatically.

### 7. Audit one complete task attempt

Save task/template/rollout IDs; full messages; per-call exact prefix and generated token IDs; raw text; tools and results; prompt/config/model provenance; stop reasons; report/working-note token boundaries; source-state snapshots; original scores; and independent checks. Save incrementally to persistent storage.

Identify P0 (before working reasoning) and P1 (before final report) according to the agreed protocol. If no valid reasoning/report boundary exists, flag it rather than invent it. Test replay agreement on a small original-execution capture before using replay for research.

Done when: a human can reconstruct the evidence, actual context and final claim from saved records, and extraction positions are unambiguous.

### 8. Only then launch the behavioral pilot

Use a fixed rollout/time/token budget. Preserve honest, misleading, uncertain and invalid runs. Annotate explicit verbalized deception evidence versus other misleading reports; incomplete reasoning remains uncertain. Evaluate whether both groups occur before scaling. Repeated samples and error-count variants of this one codebase are not independent task templates.

## Current status

Completed: exact source import, provenance, byte verification, compatibility audit, implementation checklist.

Not completed: Qwen provider, integration patches, elicitation protocol, Docker/GPU execution, behavior collection, reasoning capture or probe training. No original environment behavior has been modified.

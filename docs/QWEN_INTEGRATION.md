# Implemented Qwen integration

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

## Scope and status

The integration is implemented without modifying the 101 reference upstream files. `scripts/prepare_qwen_environment.py` verifies those originals and makes a generated build beneath ignored `work/`. It copies our adapter into that build and changes exactly four upstream files: provider factory, Pre-commit Hook agent loop, step loop, and Dockerfile. Each build contains a unified diff and SHA-256 manifest.

This is a cross-model adaptation of the **shipped default Pre-commit Hook configuration**, with the exact default task/system prompt and 258-error workspace. It is not an exact replication of the paper's GPT-OSS-specific deception intervention settings. The source comparison is tested. Generation is greedy for initial technical validation; repeated greedy runs are not independent behavioral samples.

No Qwen weights were downloaded or executed during implementation. Container execution is unverified: the desktop session could not access the Docker daemon socket. The checked integration tests use scripted responses, the actual patched upstream provider factory/step loop, and mocked command execution. They do not establish GPU, container, or behavioral success.

## Actual supported topology

A notebook worker and Docker host share a private **local POSIX filesystem**:

```
notebook Python: Qwen + raw generation logger
          ↕ private generation request/response files
Docker root controller: original task loop + remote Qwen provider
          ↕ upstream privilege-dropped command execution
disposable task user: /agent workspace
```

The file queue has no public endpoint and no shell-execution function. It is not a remote networking connector. Only the trusted controller accesses `/opt/bridge`; `/opt` remains root-only, while model commands run as `dev`. Docker runs with network disabled and only the per-run bridge, output and config mounts. Do not mount your home directory, repository, credentials or Docker socket into the task container.

**A separate hosted Colab runtime is not connected by this implementation.** Use a notebook on a Docker-capable GPU host for the first deployment proof. Colab-to-another-host transport remains a future explicit deployment decision. Google Drive/FUSE is not a supported queue filesystem: the transport relies on local atomic hard-link publication. Copy/archive completed results to persistent storage separately if needed.

## Files and responsibilities

- `src/qwen_adapter/local_model.py`: deferred torch/Transformers imports, model/tokenizer revision alignment, bounded generation and metadata. No model loading at module import.
- `protocol.py`: strict single execute_command tool parsing; no JSON recovery from incidental text, no command repair.
- `remote_provider.py`: original BaseProvider interface, canonical assistant/tool history, request matching and tool-result logging.
- `spool.py`: atomic write-once publication and bounded waits; private shared filesystem is the access-control boundary. Hashes provide integrity correlation, not authentication against a hostile filesystem owner.
- `worker.py`: claim requests once, validate settings/hash, persist input/raw generation before stop/parser checks, then publish parsed output or an error.
- `settings.py`: fail-fast supported-model/protocol/settings validation.
- `container_entry.py`: runs the original entrypoint and exports output ownership to the host user on exit.
- `audit.py`: records original score, strict mypy under original config, marker/config/hook-bit and Git diagnostics. These do not establish semantic correctness, actual historical hook execution or deception. Submitted-hook functional testing and human report annotation remain required before research collection.
- `scripts/prepare_qwen_environment.py`: source verification, generated integration and auditable diff.
- `scripts/run_precommit_qwen.py`: capstone-aware build/launch, avoiding the original launcher's assumption that the framework is the Git root.
- `configs/precommit_hook_qwen_original.json`: explicit setup and original default prompts. JSON is valid input to the existing YAML loader.
- `notebooks/02_precommit_qwen.ipynb`: prepare, load worker, launch one task and inspect outputs. Delivered unexecuted.

## Setup and offline validation

From the capstone repository root, use Python 3.11 or 3.12 for eventual model execution:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-controller.txt
python -m unittest discover -s tests -v
python scripts/verify_upstream.py
```

The offline suite needs only the original controller dependencies; it does not import real torch or download model weights. Separate model execution additionally needs `python -m pip install -r requirements.txt`. Keep host-controller and notebook environments separate if desired.

Prepare an inspectable build/config without Docker or Qwen:

```sh
python scripts/run_precommit_qwen.py --run-dir results/precommit_review --prepare-only
```

Use a fresh run directory. Inspect its config.json and launch.json, and the generated build's qwen_adaptation.patch. The prepare operation deliberately refuses to overwrite an existing run/build. It creates no commits, nested Git repository, or network listener.

For actual execution, follow the notebook: start the worker before launching the controller using the prepared commands. The command-line launcher can also launch a fresh run if a separately started worker is already polling that run's bridge directory; coordinate the new path explicitly. Do not launch the prepared container twice. The CPU container does not need GPU passthrough because inference stays in the notebook process.

## Reasoning capture and report boundaries

Only **original-prompt mode** is implemented. No working-notes elicitation or deception-related instruction was added. Text before a valid tool call is retained as spontaneous working text, returned in the upstream reasoning field for display, and kept in actual assistant content for subsequent tokenization. This is an observable explanation, not an exposed native reasoning channel or validated faithful CoT.

A complete plain-text response remains the final report, matching the original stopping convention. We do not split internal reasoning from that report by guessing. Consequently, a final turn that mixes reasoning and reporting has no validated separate boundary; this must be reviewed before adopting the proposed P1 research measurement. Missing reasoning is uncertain, not evidence for the negative class. Explicit marker-based elicitation remains disabled pending review.

The parser rejects incomplete/unknown/multiple tool calls, fenced examples, trailing ambiguous content, empty strings and malformed JSON. Such failure ends this initial integration run as incomplete rather than introducing an unapproved repair/retry prompt. Quoted plain JSON outside tool tags remains text and is never promoted to an action.

## Records and reproducibility

Per run:

- `config.json`, `launch.json`: settings, prepared launch commands and build location.
- `controller.log`, `controller/step-N/`: original loop output and workspace/message checkpoints.
- `controller/qwen_outcome_checks.json`: supplementary diagnostics after ordinary completion or max steps.
- `bridge/CALL.request.json`: exact structured generation request and settings hash.
- `bridge/CALL.input.json`: exact prefix token IDs, model/template/version metadata, saved before generation/context-budget checks.
- `bridge/CALL.generation.json`: raw decoded output, original input/generated IDs, stop reason and model metadata; retained even if parsing fails.
- `bridge/CALL.response.json`: parsed result or explicit error, matched to the request.
- `bridge/CALL.tool_result.json`: original tool result matched to the action ID.

Canonical message serialization can normalize tool markup. It is the saved per-call input IDs, not a reconstructed transcript, that define activation replay. No full activation archive or probes are implemented by this integration. Model metadata pins the resolved commit; requested revision defaults to main for first smoke use and should be fixed to a commit before research.

Each generation resets the configured seed; this policy is explicitly logged. Greedy output need not be bitwise identical across hardware. If sampling is enabled later, the fixed-per-call-seed policy and sampling parameters must be considered in the experimental protocol.

## Failure and recovery policy

One active worker and one controller per run. Request claims and records are write-once. Model settings must match the controller config. A claimed request whose worker crashes is not automatically regenerated. A timed-out request cannot cause command execution after the controller has stopped.

Controller exceptions create an incomplete record and workspace checkpoint where possible. No automatic resume is supported: a crash between action execution and checkpoint persistence leaves uncertainty about whether an action already occurred. Do not replay the last command or mount a checkpoint into another run without a manual audit. Full exactly-once recovery is not claimed. A forced container kill can also prevent final ownership export/diagnostics.

The timeout stops/removes the container. The notebook worker stop event cannot interrupt a model.generate already in progress; wait for that thread to finish or restart the kernel before reusing the model. No silent context truncation occurs. Oversized prompts produce an error record with available input IDs.

## Verification performed

- Original source integrity: 101 hashes unchanged.
- 14 offline tests: strict parsing, multiline commands, raw evidence retention, truncation handling, request settings mismatch, immutable publication, timeout, original prompt equality, real factory/config forwarding, real two-turn step-loop flow with mocked shell, and mocked local generation/context-budget paths.
- Official Qwen tokenizer chat template rendered directly without model loading: working text retained once, tool call serialized once, tool results retained, assistant generation prefix present.
- Static checks on new code and syntax parsing of generated upstream Python.
- Prepared launcher/build inspection without Docker/model execution.

Untested: real model dependency installation on the GPU runtime, weights/inference, Linux privilege boundary, Docker build and mypy build pins, actual notebook/controller sharing, real working-text yield, replay agreement, hook functional verification and behavioral annotation. These are gates, not claimed successes.

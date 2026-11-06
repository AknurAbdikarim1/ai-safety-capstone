# Repository file inventory

Updated 6 November 2026; covers **223 files**, including uncommitted project files and this inventory.

Each entry is one sentence describing the file and when to keep or use it; paths are relative to the repository root.

Scope: all Git-tracked and unignored project files; excludes Git internals, ignored work/build trees, caches, model weights, and generated run/activation artifacts other than tracked placeholders.

Labels describe usage, not deletion permission: alternative upstream providers may be imported indirectly, and the complete reference snapshot should stay intact for checksum verification.

Runtime JSON/token bundles are traced by the research log and model report rather than enumerated as source files here; the explicitly requested Gemma evidence ZIP and readable exports are retained in Git but remain generated artifacts outside this inventory’s count.

## Project setup

- [.gitignore](../.gitignore) — [Active setup] Excludes caches, generated builds, model weights, secrets and runtime artifacts from Git; keep it for all development and runs.
- [AGENTS.md](../AGENTS.md) — [Development rules] Defines commit and staging rules for coding agents; keep it while using agent assistance.
- [README.md](../README.md) — [Project guide] Explains setup, smoke tests and integration entry points; consult it when starting or sharing the project.
- [requirements-controller.txt](../requirements-controller.txt) — [Controller/test dependencies] Installs the copied upstream framework for host-side controller imports and offline tests; it does not install model weights.
- [requirements.txt](../requirements.txt) — [Model dependencies] Lists the Python libraries needed to load Qwen and save activations; install it in the inference runtime.

## Our model and adapter code

- [src/qwen_adapter/__init__.py](../src/qwen_adapter/__init__.py) — [Active package marker] Makes the Qwen integration importable as a Python package; keep it with the adapter.
- [src/qwen_adapter/audit.py](../src/qwen_adapter/audit.py) — [Supplementary checks] Records mypy, Git, marker, hook-bit and config diagnostics after a task; retain it as mechanical evidence rather than a complete verifier or deception classifier.
- [src/qwen_adapter/container_entry.py](../src/qwen_adapter/container_entry.py) — [Active container wrapper] Starts the original task entrypoint, exports clean or small-source submissions when selected and makes output host-readable; needed by the adapted Docker image.
- [src/qwen_adapter/local_model.py](../src/qwen_adapter/local_model.py) — [Active inference code] Loads aligned Qwen model/tokenizer revisions, renders the selected XML or serial condition, enforces context limits and generates token records; needed wherever Qwen runs.
- [src/qwen_adapter/manual_exchange.py](../src/qwen_adapter/manual_exchange.py) — [Active manual-transfer code] Exports requests, generates Colab bundles with optional per-record durable retention and validates/archives returned bundles under the run directory before releasing the controller; needed for the current Colab–Mac workflow.
- [src/qwen_adapter/protocol.py](../src/qwen_adapter/protocol.py) — [Active parsing code] Validates legacy XML/serial calls and the thinking condition’s phased records, separating reasoning and reports without repairing commands; needed before interpreting or executing output.
- [src/qwen_adapter/remote_provider.py](../src/qwen_adapter/remote_provider.py) — [Active controller adapter] Implements the upstream provider interface using generation requests and tool-result history; needed inside the task controller.
- [src/qwen_adapter/settings.py](../src/qwen_adapter/settings.py) — [Active validation code] Rejects unsupported model, protocol and generation settings before launch; needed when checking an experiment configuration.
- [src/qwen_adapter/spool.py](../src/qwen_adapter/spool.py) — [Active transport utility] Publishes write-once JSON records and waits for matched responses on local POSIX storage; needed by the shared-folder and manual workflows.
- [src/qwen_adapter/worker.py](../src/qwen_adapter/worker.py) — [Active generation handler] Processes queued requests, preserves raw evidence and returns parsed responses or errors; used by manual generation and optional background-worker mode.
- [src/run_model.py](../src/run_model.py) — [Smoke-test code] Runs a short Qwen inference and saves selected last-input-token activations plus metadata; use it to validate GPU setup rather than study deception.

## Our scripts

- [scripts/calibrate_qwen_tools.py](../scripts/calibrate_qwen_tools.py) — [Optional diagnostic] Compares simple tool formatting with and without a reminder using explicitly simulated results; keep it to reproduce calibration, not as research-dataset collection code.
- [scripts/manual_exchange.py](../scripts/manual_exchange.py) — [Manual-transfer command] Shows pending requests and exports/imports exchange files; use it in the Mac terminal for each manual Colab turn.
- [scripts/prepare_qwen_environment.py](../scripts/prepare_qwen_environment.py) — [Build-preparation command] Copies verified originals into an ignored build and applies the narrow Qwen adaptation with a diff and manifest; needed before building the task image.
- [scripts/run_precommit_qwen.py](../scripts/run_precommit_qwen.py) — [Launch command] Prepares a fresh run and builds/starts its Docker controller with limits, including manual transfer and clean/small-source reference/submission verification; needed to launch the current task setup.
- [scripts/verify_upstream.py](../scripts/verify_upstream.py) — [Integrity command] Compares copied upstream files with the recorded SHA-256 manifest; run it before preparing builds or reviewing source preservation.

## Experiment configurations

- [configs/precommit_hook_qwen_format_reminder.json](../configs/precommit_hook_qwen_format_reminder.json) — [Diagnostic condition] Adds only the neutral tool-format reminder and provenance to the baseline setup; keep it to reproduce the tested adaptation.
- [configs/precommit_hook_qwen_original.json](../configs/precommit_hook_qwen_original.json) — [Baseline configuration] Records the shipped default task prompts and Qwen settings without reasoning elicitation; keep it as the comparison condition and initial setup.

## Execution notebooks

- [notebooks/01_model_setup.ipynb](../notebooks/01_model_setup.ipynb) — [Smoke-test notebook] Sets up Colab and inspects saved inference/activation outputs; needed when validating or reproducing the basic model pipeline.
- [notebooks/02_precommit_qwen.ipynb](../notebooks/02_precommit_qwen.ipynb) — [Alternative deployment notebook] Coordinates inference and Docker on a host with shared local storage; keep for future same-host execution rather than the current separate Colab–Mac setup.
- [notebooks/03_manual_colab_mac.ipynb](../notebooks/03_manual_colab_mac.ipynb) — [Current execution notebook] Loads Qwen in Colab and exchanges request/response bundles with Docker on the Mac; use it for interactive manual attempts.

## Offline tests

- [tests/test_format_reminder_config.py](../tests/test_format_reminder_config.py) — [Configuration regression test] Confirms the reminder matches calibration and leaves other task/model settings unchanged; run when editing the diagnostic condition.
- [tests/test_manual_exchange.py](../tests/test_manual_exchange.py) — [Offline regression tests] Checks token-preserving manual transfers and rejection of stale, mismatched or altered bundles; run after exchange changes without Docker or Qwen.
- [tests/test_qwen_integration.py](../tests/test_qwen_integration.py) — [Offline regression tests] Checks parsing, transport, generation handling and the patched upstream task loop using test doubles; run after adapter or integration changes without loading Qwen.
- [tests/test_tool_calibration.py](../tests/test_tool_calibration.py) — [Offline diagnostic tests] Checks the simple calibration harness with fake generations and raw-failure retention; keep while maintaining the calibration script.

## Documentation and executed evidence

- [docs/FILE_INVENTORY.md](../docs/FILE_INVENTORY.md) — [Navigation reference] Describes every tracked or unignored project file in one sentence; update it when project files are added, moved or removed.
- [docs/MANUAL_COLAB_MAC.md](../docs/MANUAL_COLAB_MAC.md) — [Current workflow guide] Explains Docker checks, Colab preparation, manual file transfer and failure handling; follow it for the current deployment.
- [docs/PRECOMMIT_ADAPTATION.md](../docs/PRECOMMIT_ADAPTATION.md) — [Source-adaptation record] Describes the source import and planned adaptation sequence with an implementation update; keep it as provenance and consult newer integration guidance for current execution.
- [docs/PRECOMMIT_QWEN_COMPATIBILITY.md](../docs/PRECOMMIT_QWEN_COMPATIBILITY.md) — [Historical audit] Documents the initial source inspection and compatibility problems; keep it to explain integration decisions rather than treat it as current runtime status.
- [docs/QWEN_IMPLEMENTATION_REVIEW.md](../docs/QWEN_IMPLEMENTATION_REVIEW.md) — [Historical verification report] Records the initial 14-test implementation review and its limitations; preserve it as a dated record rather than the latest test count.
- [docs/QWEN_INTEGRATION.md](../docs/QWEN_INTEGRATION.md) — [Integration reference] Explains the adapter, generated patches, local transport and its original verification limits; use it for architecture and pair it with the newer manual guide and research log.
- [docs/QWEN_SETUP_AND_FILE_PLAN.md](../docs/QWEN_SETUP_AND_FILE_PLAN.md) — [Historical implementation plan] Describes proposed deployment options and file changes; keep it for design history and use the implementation guide for supported behavior.
- [docs/RESEARCH_LOG.md](../docs/RESEARCH_LOG.md) — [Daily evidence log] Records completed work, observed results, limitations and next steps; update it after meaningful experiment activity.
- [docs/RESEARCH_PLAN.md](../docs/RESEARCH_PLAN.md) — [Research roadmap] Records the staged study design, annotation criteria, extraction positions and evaluation gates; consult it before advancing the experiment.
- [docs/validation/2026-10-22_smoke_run.ipynb](../docs/validation/2026-10-22_smoke_run.ipynb) — [Executed evidence] Preserves the first saved smoke-test notebook; keep it for historical verification and do not use it as a clean execution template.
- [docs/validation/2026-10-22_smoke_run2.ipynb](../docs/validation/2026-10-22_smoke_run2.ipynb) — [Executed evidence] Preserves the measured smoke run with saved timing and memory output; keep it to substantiate the recorded GPU results.
- [docs/validation/2026-10-27_qwen2.5-3b_precommit_tool-diagnostics.ipynb.ipynb](../docs/validation/2026-10-27_qwen2.5-3b_precommit_tool-diagnostics.ipynb.ipynb) — [Executed evidence] Preserves the researcher-saved tool-diagnostic session with its current double notebook extension; keep it for traceability rather than as a fresh-run template.

## Empty-directory placeholders

- [activations/.gitkeep](../activations/.gitkeep) — [Placeholder] Keeps the activation directory in Git while generated vectors remain ignored; it contains no activation data.
- [data/.gitkeep](../data/.gitkeep) — [Placeholder] Keeps the currently empty data directory in Git; it contains no task dataset.
- [results/.gitkeep](../results/.gitkeep) — [Placeholder] Keeps the results directory in Git while runtime outputs remain ignored; it contains no experiment results.

## Upstream provenance

- [experiment_sources/UPSTREAM_MANIFEST.json](../experiment_sources/UPSTREAM_MANIFEST.json) — [Provenance record] Stores the source commit and checksums of all 101 copied upstream files; needed to verify that the reference snapshot remains unchanged.

## Copied upstream setup and configuration

- [experiment_sources/agent-interp-envs/.dockerignore](../experiment_sources/agent-interp-envs/.dockerignore) — [Active upstream build configuration] Excludes unwanted files from the generated Docker build context; preserve it when preparing images.
- [experiment_sources/agent-interp-envs/.python-version](../experiment_sources/agent-interp-envs/.python-version) — [Upstream environment reference] Records the original preferred Python version for compatible tooling; keep it as source context while checking the actual execution runtime separately.
- [experiment_sources/agent-interp-envs/LICENSE](../experiment_sources/agent-interp-envs/LICENSE) — [Required attribution] Preserves the upstream MIT license; keep it with the copied source.
- [experiment_sources/agent-interp-envs/README.md](../experiment_sources/agent-interp-envs/README.md) — [Upstream reference] Describes the broader original framework and environments; keep it for context but use capstone instructions for our nested Qwen integration.
- [experiment_sources/agent-interp-envs/configs/precommit_hook/default.yaml](../experiment_sources/agent-interp-envs/configs/precommit_hook/default.yaml) — [Baseline source reference] Contains the shipped Claude/default prompts and task settings from which our baseline was adapted; preserve it unchanged for comparison.
- [experiment_sources/agent-interp-envs/configs/precommit_hook/precommit_hook.yaml](../experiment_sources/agent-interp-envs/configs/precommit_hook/precommit_hook.yaml) — [Alternative upstream condition] Contains the shipped DeepSeek configuration and a different error-count variant; keep it for reference rather than use it as our Qwen configuration.
- [experiment_sources/agent-interp-envs/pyproject.toml](../experiment_sources/agent-interp-envs/pyproject.toml) — [Active upstream build metadata] Defines the framework package and controller dependencies installed into the task image; preserve it for reproducible builds.
- [experiment_sources/agent-interp-envs/uv.lock](../experiment_sources/agent-interp-envs/uv.lock) — [Upstream reproducibility reference] Locks dependencies for the original uv workflow; keep it for provenance although our current pip-based image does not directly use this lock.

## Copied upstream Pre-commit Hook controller

- [experiment_sources/agent-interp-envs/environments/precommit_hook/Dockerfile](../experiment_sources/agent-interp-envs/environments/precommit_hook/Dockerfile) — [Active upstream image recipe] Defines Linux dependencies, task-source installation and privilege separation; use its generated adapted copy to build our task image.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/README.md](../experiment_sources/agent-interp-envs/environments/precommit_hook/README.md) — [Task reference] Describes the original hook task, variants and scoring flags; keep it to understand what is being reproduced.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/agent.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/agent.py) — [Active upstream loop] Creates the provider and runs/checkpoints task turns; our generated copy adds Qwen configuration forwarding and failure records.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/apply_patch.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/apply_patch.py) — [Preserved editing utility] Implements the original patch-editing tool and CLI included in the image; keep it unchanged even though our selected tool interface is the shell.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/entrypoint.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/entrypoint.py) — [Active task setup] Installs the selected source variant and Git workspace before starting the agent; preserve its task and permission behavior.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/generate_variants.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/generate_variants.py) — [Active image-build utility] Blends typed and untyped source and measures mypy errors to create intermediate variants; needed during the original image build.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/pyproject.toml](../experiment_sources/agent-interp-envs/environments/precommit_hook/pyproject.toml) — [Active task requirements] Defines the ingestion project and strict mypy settings the model must satisfy; preserve it as part of the experimental task.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/run_step.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/run_step.py) — [Active action handler] Processes model responses and executes task tools; our generated copy disables inappropriate tool-recovery paths for Qwen.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/score.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/score.py) — [Original telemetry] Detects shortcut patterns from commands and files; preserve its output alongside stronger checks rather than use it as a deception label.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/states.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/states.py) — [Active state support] Tracks commands and task state and delegates workspace checkpointing; needed for the original loop and saved evidence.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/tools.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/tools.py) — [Active tool definitions] Defines the shell and optional task tools; our current configuration selects only execute_command.

## Copied corrected task source: src_0

- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/__init__.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/__init__.py) — [Corrected task control] This original source copy marks the ingestion-source package for Python imports; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/api_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/api_source.py) — [Corrected task control] This original source copy implements JSON API polling and ingestion; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/cache.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/cache.py) — [Corrected task control] This original source copy implements a time-limited cache for expensive lookups; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/cli.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/cli.py) — [Corrected task control] This original source copy provides the ingestion service command-line interface; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/config.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/config.py) — [Corrected task control] This original source copy loads and merges application configuration; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/csv_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/csv_source.py) — [Corrected task control] This original source copy reads records from CSV inputs; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/db.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/db.py) — [Corrected task control] This original source copy manages database connections and query execution; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/db_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/db_source.py) — [Corrected task control] This original source copy reads ingestion records from SQL databases; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/logging_setup.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/logging_setup.py) — [Corrected task control] This original source copy configures ingestion-service logging; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/metrics.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/metrics.py) — [Corrected task control] This original source copy tracks ingestion counters and performance metrics; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/models.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/models.py) — [Corrected task control] This original source copy defines ingestion records and related data models; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/scheduler.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/scheduler.py) — [Corrected task control] This original source copy schedules recurring ingestion jobs; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/transform.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/transform.py) — [Corrected task control] This original source copy defines data-transformation operations and pipelines; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/validation.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/validation.py) — [Corrected task control] This original source copy checks records against schema requirements; preserve it unchanged for the zero-error control and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/writer.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_0/writer.py) — [Corrected task control] This original source copy buffers and writes records to the data warehouse; preserve it unchanged for the zero-error control and generation of intermediate variants.

## Copied baseline task source: src_258

- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/__init__.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/__init__.py) — [Baseline task input] This original source copy marks the ingestion-source package for Python imports; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/api_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/api_source.py) — [Baseline task input] This original source copy implements JSON API polling and ingestion; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/cache.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/cache.py) — [Baseline task input] This original source copy implements a time-limited cache for expensive lookups; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/cli.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/cli.py) — [Baseline task input] This original source copy provides the ingestion service command-line interface; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/config.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/config.py) — [Baseline task input] This original source copy loads and merges application configuration; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/csv_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/csv_source.py) — [Baseline task input] This original source copy reads records from CSV inputs; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/db.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/db.py) — [Baseline task input] This original source copy manages database connections and query execution; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/db_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/db_source.py) — [Baseline task input] This original source copy reads ingestion records from SQL databases; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/logging_setup.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/logging_setup.py) — [Baseline task input] This original source copy configures ingestion-service logging; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/metrics.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/metrics.py) — [Baseline task input] This original source copy tracks ingestion counters and performance metrics; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/models.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/models.py) — [Baseline task input] This original source copy defines ingestion records and related data models; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/scheduler.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/scheduler.py) — [Baseline task input] This original source copy schedules recurring ingestion jobs; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/transform.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/transform.py) — [Baseline task input] This original source copy defines data-transformation operations and pipelines; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/validation.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/validation.py) — [Baseline task input] This original source copy checks records against schema requirements; preserve it unchanged for the selected 258-error task and generation of intermediate variants.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/writer.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_258/writer.py) — [Baseline task input] This original source copy buffers and writes records to the data warehouse; preserve it unchanged for the selected 258-error task and generation of intermediate variants.

## Copied alternative task source: src_602

- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/__init__.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/__init__.py) — [Alternative task input] This original source copy marks the ingestion-source package for Python imports; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/api_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/api_source.py) — [Alternative task input] This original source copy implements JSON API polling and ingestion; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/cache.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/cache.py) — [Alternative task input] This original source copy implements a time-limited cache for expensive lookups; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/cli.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/cli.py) — [Alternative task input] This original source copy provides the ingestion service command-line interface; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/config.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/config.py) — [Alternative task input] This original source copy loads and merges application configuration; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/csv_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/csv_source.py) — [Alternative task input] This original source copy reads records from CSV inputs; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/db.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/db.py) — [Alternative task input] This original source copy manages database connections and query execution; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/db_source.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/db_source.py) — [Alternative task input] This original source copy reads ingestion records from SQL databases; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/logging_setup.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/logging_setup.py) — [Alternative task input] This original source copy configures ingestion-service logging; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/metrics.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/metrics.py) — [Alternative task input] This original source copy tracks ingestion counters and performance metrics; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/models.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/models.py) — [Alternative task input] This original source copy defines ingestion records and related data models; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/scheduler.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/scheduler.py) — [Alternative task input] This original source copy schedules recurring ingestion jobs; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/transform.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/transform.py) — [Alternative task input] This original source copy defines data-transformation operations and pipelines; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/validation.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/validation.py) — [Alternative task input] This original source copy checks records against schema requirements; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.
- [experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/writer.py](../experiment_sources/agent-interp-envs/environments/precommit_hook/src_602/writer.py) — [Alternative task input] This original source copy buffers and writes records to the data warehouse; preserve it unchanged for the preserved higher-error variant, not selected by our current Qwen config.

## Copied upstream launch tools

- [experiment_sources/agent-interp-envs/scripts/env_registry.py](../experiment_sources/agent-interp-envs/scripts/env_registry.py) — [Upstream launcher support] Maps environment names and manages Git snapshot build contexts; retain it as source while our launcher handles the nested repository explicitly.
- [experiment_sources/agent-interp-envs/scripts/gateway_sidecar.py](../experiment_sources/agent-interp-envs/scripts/gateway_sidecar.py) — [Optional cloud infrastructure] Proxies provider requests and injects credentials in Modal deployments; retain it as upstream source and do not use it for manual local-Qwen exchange.
- [experiment_sources/agent-interp-envs/scripts/resume.py](../experiment_sources/agent-interp-envs/scripts/resume.py) — [Optional upstream continuation] Resumes original Docker checkpoints; keep it for reference and do not use it as an automatic recovery path for our manual runs.
- [experiment_sources/agent-interp-envs/scripts/resume_modal.py](../experiment_sources/agent-interp-envs/scripts/resume_modal.py) — [Optional cloud continuation] Resumes original checkpoints on Modal; retain it for future investigation rather than current Qwen run recovery.
- [experiment_sources/agent-interp-envs/scripts/run.py](../experiment_sources/agent-interp-envs/scripts/run.py) — [Alternative upstream launcher] Builds and launches Docker rollouts using original Git-root assumptions; keep it for reference and use our capstone launcher for the nested copy.
- [experiment_sources/agent-interp-envs/scripts/run_common.py](../experiment_sources/agent-interp-envs/scripts/run_common.py) — [Upstream launcher support] Resolves configurations, build inputs, output layouts and judge commands; retained for the original runners rather than our manual launcher.
- [experiment_sources/agent-interp-envs/scripts/run_modal.py](../experiment_sources/agent-interp-envs/scripts/run_modal.py) — [Optional cloud runner] Launches original environments on Modal; keep it for possible future cloud deployment rather than current manual execution.
- [experiment_sources/agent-interp-envs/scripts/smoke_modal.py](../experiment_sources/agent-interp-envs/scripts/smoke_modal.py) — [Optional cloud diagnostic] Runs original mock-provider checks on Modal; retain it for reference because the copied snapshot omits other registered environments.

## Copied upstream shared framework and providers

- [experiment_sources/agent-interp-envs/src/agent_interp_envs/__init__.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/__init__.py) — [Active package marker] Makes the copied framework importable; needed for its controller modules.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/checkpoint.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/checkpoint.py) — [Active checkpoint support] Saves conversation/state/filesystem snapshots and forwards provider settings on restoration; retain it although automatic recovery is not validated for our runs.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/config.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/config.py) — [Active config loader] Reads task configuration through YAML parsing, including our JSON configuration; needed when the container starts.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/cot_judge.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/cot_judge.py) — [Optional reasoning-intervention support] Uses an LLM judge to classify reasoning sentences for rejection sampling; keep it as reference and leave it disabled in our experiment.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/__init__.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/__init__.py) — [Other-task reference] Exposes dataset-loader utilities for original coding benchmarks; retain it with the framework although Pre-commit Hook does not use those datasets.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/base.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/base.py) — [Other-task reference] Defines coding-sample and dataset-loader interfaces; keep it for upstream completeness rather than the current hook task.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/evilgenie.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/evilgenie.py) — [Other-task reference] Loads EvilGenie benchmark problems; keep it as upstream code and do not treat it as our collected dataset.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/impossiblebench.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/dataloaders/impossiblebench.py) — [Other-task reference] Loads ImpossibleBench problems; keep it as upstream code rather than use it for the current hook experiment.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/episode_end.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/episode_end.py) — [Optional run-finalization utility] Produces consolidated transcript and run-health records for original workflows; keep it for future analysis rather than assume our launcher invokes it.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/grading.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/grading.py) — [Optional API grading support] Runs transcript autoraters and aggregates their verdicts; retain it as reference while our initial annotations remain separate and human-reviewed.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/print_helpers.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/print_helpers.py) — [Active display support] Formats task history and status output; needed by the original loop and providers.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/__init__.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/__init__.py) — [Active provider factory] Registers and constructs the original providers; our generated copy adds the local-Qwen controller option.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/_keys.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/_keys.py) — [Indirect dependency] Resolves API credentials for original providers and gateways; preserve it because retained provider modules import it even though manual Qwen needs no API key.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/anthropic_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/anthropic_provider.py) — [Alternative provider] Implements Anthropic API generation and reasoning handling; preserve it for upstream imports/reference although Qwen does not call that API.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/base.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/base.py) — [Active provider contract] Defines generation and history methods that our Qwen provider implements; preserve it for interface compatibility.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/deepseek_v4_template.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/deepseek_v4_template.py) — [Alternative model support] Renders and parses the original DeepSeek completion protocol; retain it for provider imports/reference rather than Qwen formatting.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/fireworks_completions_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/fireworks_completions_provider.py) — [Alternative provider] Implements raw DeepSeek completions with prefill support; preserve it as an indirectly imported upstream option, not a Qwen reasoning channel.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/fireworks_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/fireworks_provider.py) — [Alternative provider] Implements Fireworks chat generation and reasoning fields; preserve it for compatibility/reference rather than our local inference path.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/minimax_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/minimax_provider.py) — [Alternative provider] Implements MiniMax API generation; preserve it for upstream imports/reference while leaving it unused as an inference backend.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/mock_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/mock_provider.py) — [Optional offline provider] Emits scripted actions without model/API calls; retain it for original-framework testing rather than behavioral evidence.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/moonshot_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/moonshot_provider.py) — [Alternative provider] Implements Moonshot/Kimi API responses and reasoning fields; preserve it for compatibility rather than current local generation.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/openai_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/openai_provider.py) — [Alternative provider] Implements OpenAI Responses API generation and history conversion; preserve it for upstream imports/reference rather than local Qwen inference.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/openrouter_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/openrouter_provider.py) — [Alternative provider] Implements OpenRouter generation, reasoning fields and tool calls; preserve it for compatibility although current Qwen runs locally.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/rejection_provider.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/providers/rejection_provider.py) — [Disabled intervention reference] Resamples reasoning sentences flagged by a judge; keep it for upstream compatibility and do not enable it in our initial Qwen study.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/py.typed](../experiment_sources/agent-interp-envs/src/agent_interp_envs/py.typed) — [Package typing marker] Marks the framework as providing typing information; retain it as package metadata rather than confuse it with the task marker Qwen must create.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/runner.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/runner.py) — [Alternative shared loop] Provides a reusable runner for upstream environments; retained for framework compatibility while Pre-commit Hook uses its own agent loop.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/runs.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/runs.py) — [Upstream analysis support] Reads rollout directories and classifies completion/error metadata; retained for original runner and grading utilities.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/tool_calling.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/tool_calling.py) — [Active execution support] Runs shell commands with privilege dropping, timeouts and output limits and supplies shared tool utilities; needed by the task loop and audits.
- [experiment_sources/agent-interp-envs/src/agent_interp_envs/types.py](../experiment_sources/agent-interp-envs/src/agent_interp_envs/types.py) — [Active shared interface] Defines response, tool-call and tool-result structures used by the original framework and our adapter; preserve it for compatibility.

## Serial-interface feasibility condition

- [src/qwen_adapter/serial_format.py](../src/qwen_adapter/serial_format.py) — [Opt-in serial formatter] Renders the Qwen-specific serial ChatML history and detects tool-result boundaries; use only for the separately versioned serial condition.
- [configs/precommit_hook_qwen_serial.json](../configs/precommit_hook_qwen_serial.json) — [Offline-tested diagnostic condition] Selects the serial tool format and pins the previously observed model revision; retain separately from baseline configurations.
- [notebooks/04_serial_interface_colab_mac.ipynb](../notebooks/04_serial_interface_colab_mac.ipynb) — [Serial-condition entry point] Loads matching serial settings for manual Colab transfer in a fresh runtime; use with the bounded diagnostic launcher after verifying the upload package.
- [tests/test_serial_interface.py](../tests/test_serial_interface.py) — [Serial regression checks] Tests strict calls, generation stopping arguments, observation history and manual boundary bundles using doubles; run without Qwen or Docker.
- [docs/QWEN_SERIAL_INTERFACE.md](../docs/QWEN_SERIAL_INTERFACE.md) — [Current implementation review] Records the serial condition, offline checks, limitations and next live-evaluation gate; consult before running this condition.

- [docs/validation/2026-10-28_serial_prompt_examples.txt](../docs/validation/2026-10-28_serial_prompt_examples.txt) — [Offline illustration] Preserves rendered serial-format prompts with explicitly scripted observations for review; do not treat them as executed model or Docker evidence.

- [scripts/run_serial_diagnostics.py](../scripts/run_serial_diagnostics.py) — [Bounded interface launcher] Publishes versioned manual diagnostic requests with explicit command spellings and configurable conditions, explicit case subsets and supplementary budgets, and records real Docker outputs and human report reviews; use only for interface evaluation, not behavioral collection.
- [scripts/package_serial_diagnostics.py](../scripts/package_serial_diagnostics.py) — [Upload packaging command] Builds the allowlisted serial Colab ZIP and source/archive checksums under ignored work; use when preparing a matching upload package.
- [tests/test_serial_diagnostics.py](../tests/test_serial_diagnostics.py) — [Offline orchestration checks] Verifies case progression, explicit separator acceptance, failure-output retention and first-failure action blocking using scripted generation and Docker doubles; retain as launcher regression coverage.
- [docs/SERIAL_DIAGNOSTICS.md](SERIAL_DIAGNOSTICS.md) — [Current execution protocol] Specifies fresh-T4 setup, exact Mac commands, four-case checklist, evidence locations and stop rules; follow for the bounded serial gate.

## Clean-source autonomous feasibility condition

- [configs/precommit_hook_qwen_clean_serial.json](../configs/precommit_hook_qwen_clean_serial.json) — [Clean task condition] Selects zero-error source, original release prompts, ten-call/30-minute limits and independent hook checks; use separately from the original 258-error condition.
- [src/qwen_adapter/clean_release.py](../src/qwen_adapter/clean_release.py) — [Independent release checks] Validates clean-source artifacts and dispatches optional ten-error checks, exercising hooks as dev in isolated Git fixtures with reference preflight; retain for clean-task outcome evidence, not deception labeling.
- [tests/test_clean_release.py](../tests/test_clean_release.py) — [Offline clean-task checks] Tests artifact tamper detection, Git/hook fixture behavior with doubled mypy and bounded prepare-only setup; use before live clean-task verification.
- [docs/CLEAN_SOURCE_RELEASE.md](CLEAN_SOURCE_RELEASE.md) — [Clean-task protocol] Defines the autonomous goal, condition differences, limits, verifier scope, manual commands and evidence paths; follow before launching the clean-source attempt.

- [docs/TASK_GAMING_PAPER_REVIEW.md](TASK_GAMING_PAPER_REVIEW.md) — [Primary-source methods review] Compares the task-gaming post and linked framework with our adaptation, identifies reusable reporting environments and documents scope/interface limits; consult before adopting another upstream setup.

- [docs/REASONING_AGENT_RECOVERY_PLAN.md](REASONING_AGENT_RECOVERY_PLAN.md) — [Researched recovery proposal] Defines a separately versioned reasoning-model, constrained-action and activation-capture path with hardware estimates and staged task acceptance; consult before implementing or launching the replacement condition.

- [src/qwen_adapter/thinking_format.py](../src/qwen_adapter/thinking_format.py) — Defines the versioned thinking/action schema, per-checkpoint native history/opening handling and strict phase/activation validation; needed only for the new thinking condition.

- [src/qwen_adapter/thinking_model.py](../src/qwen_adapter/thinking_model.py) — Runs either pinned dedicated or hybrid Qwen3 thinking followed by constrained JSON and captures selected online/replayed vectors; needed in Colab for the thinking engineering pilot.

- [configs/precommit_hook_qwen3_clean_thinking.json](../configs/precommit_hook_qwen3_clean_thinking.json) — Pins the reasoning model and combined pilot settings with clean source and explicit budgets; use separately from all Qwen2.5 conditions.

- [requirements-thinking.txt](../requirements-thinking.txt) — Adds the pinned constrained-decoding dependency to existing model requirements; install only in the new thinking inference runtime.

- [notebooks/05_thinking_manual_colab_mac.ipynb](../notebooks/05_thinking_manual_colab_mac.ipynb) — Provides fresh-T4 package validation, durable phase retention, GPU smoke and manual request generation; use as the new pilot execution entry point.

- [scripts/package_thinking_manual.py](../scripts/package_thinking_manual.py) — Builds and verifies immutable allowlisted dedicated, hybrid or Kaggle thinking upload packages and checksums under work; use before the new Colab setup.

- [docs/THINKING_MANUAL_RUN.md](../docs/THINKING_MANUAL_RUN.md) — Specifies the adapted protocol, exact Mac/Colab workflow, acceptance checks and evidence paths; follow for the new manual pilot.

- [tests/test_thinking_interface.py](../tests/test_thinking_interface.py) — Checks the real schema parser, phase boundaries, failure retention, activation tampering, manual exchange and bounded launcher wiring with doubles; run offline before packaging.

- [docs/THINKING_SMOKE_DIAGNOSIS.md](THINKING_SMOKE_DIAGNOSIS.md) — Records the inspected failed thinking smoke and separately versioned bounded prompt controls with preserved evidence and decision rules; use before further live debugging.

- [configs/precommit_hook_qwen3_clean_action_prompt.json](../configs/precommit_hook_qwen3_clean_action_prompt.json) — Defines one separately versioned clean-task prompt fallback with consistent final_report instructions and incremental action while retaining model, generation settings and task goal; use only after reviewing the first thinking-task failure.

- [configs/precommit_hook_qwen3_clean_action_4096.json](../configs/precommit_hook_qwen3_clean_action_4096.json) — Defines the authorized single thinking-budget comparison at 4096 tokens with unchanged action prompt, model and other task/generation limits; use separately from the failed 2048-token runs.

- [configs/precommit_hook_qwen3_hybrid_clean.json](../configs/precommit_hook_qwen3_hybrid_clean.json) — Pins original Qwen3-4B in thinking mode for a clean-task checkpoint comparison with the prior action prompt and 4096-token cap; use separately from dedicated-thinking conditions.

- [notebooks/06_qwen3_hybrid_manual_colab_mac.ipynb](../notebooks/06_qwen3_hybrid_manual_colab_mac.ipynb) — Loads the pinned hybrid checkpoint in a fresh T4 runtime and provides one neutral smoke plus manual task generation; use only with its matching package/config.

- [docs/QWEN3_HYBRID_MANUAL_RUN.md](../docs/QWEN3_HYBRID_MANUAL_RUN.md) — Records the hybrid model/template differences, exact setup and clean-task commands, acceptance checks and larger-GPU fallback decision; follow for this checkpoint comparison.

- [docs/validation/2026-11-01_qwen3-4b_template_reference.json](../docs/validation/2026-11-01_qwen3-4b_template_reference.json) — Retains the exact pinned upstream chat template and hashes for offline boundary/history tests; keep as a reference artifact, not live inference evidence.

- [src/qwen_adapter/small_release.py](../src/qwen_adapter/small_release.py) — Checks ten-error source baselines, conservative annotation repairs and unstaged-error hook behavior without labeling intent; use for the small failing-source outcome audit.

- [configs/precommit_hook_qwen3_hybrid_small.json](../configs/precommit_hook_qwen3_hybrid_small.json) — Selects the upstream ten-error case with unchanged hybrid generation/prompts and explicit twelve-call/90-minute caps; use only for the bounded failing-source trial.

- [docs/SMALL_FAILING_SOURCE_RUN.md](../docs/SMALL_FAILING_SOURCE_RUN.md) — Defines the ten-error condition, stronger hook controls, exact manual launch/exchange commands and audit limits; follow before running or interpreting this case.

- [tests/test_small_release.py](../tests/test_small_release.py) — Exercises annotation/body/suppression checks, baseline guards, real Git staged-only detection and small-condition launcher wiring using offline fixtures and doubled mypy; run before the failing-source pilot.

- [src/qwen_adapter/notebook_exchange.py](../src/qwen_adapter/notebook_exchange.py) — Encodes validated request JSON as a safely quoted notebook cell without interpreting model text as code; use for manual Kaggle request transfer.

- [scripts/kaggle_request_cell.py](../scripts/kaggle_request_cell.py) — Emits a copy/paste cell only for an exported still-pending request; use on Mac instead of Colab file upload for Kaggle inference.

- [configs/precommit_hook_qwen3_hybrid_small_kaggle.json](../configs/precommit_hook_qwen3_hybrid_small_kaggle.json) — Labels the unchanged ten-error hybrid condition as Kaggle inference with separate platform metadata; use only with the Kaggle notebook and a fresh Mac run.

- [notebooks/07_qwen3_hybrid_kaggle_mac.ipynb](../notebooks/07_qwen3_hybrid_kaggle_mac.ipynb) — Provides GPU/package/download checks, pinned model loading, one smoke and manual inference with explicit working-files backups; use as the Kaggle execution entry point.

- [docs/KAGGLE_MANUAL_RUN.md](../docs/KAGGLE_MANUAL_RUN.md) — Documents account/GPU prerequisites, private package inputs, exact request/response steps and non-Drive evidence retention; follow before the platform migration.

- [tests/test_notebook_exchange.py](../tests/test_notebook_exchange.py) — Checks safe request quoting, stale-request rejection and Kaggle bootstrap integrity/reuse offline without GPU or browser execution; run after notebook transport changes.

- [configs/precommit_hook_qwen3_hybrid_small_kaggle_clarified.json](../configs/precommit_hook_qwen3_hybrid_small_kaggle_clarified.json) — [Prompt adaptation] Clarifies repository read/edit access and typing repair for one separately recorded ten-error Kaggle run after early abandonment.
- [docs/KAGGLE_PROMPT_CLARIFICATION_RUN.md](KAGGLE_PROMPT_CLARIFICATION_RUN.md) — [Run protocol] Records the changed instruction, fixed comparison settings and manual launch/retention procedure for the bounded clarification run.

- [configs/precommit_hook_qwen3_hybrid_small_kaggle_memory.json](../configs/precommit_hook_qwen3_hybrid_small_kaggle_memory.json) — [Profiling condition] Labels the unchanged clarified ten-error task with stage-memory telemetry; use only after reviewing the fresh-session smoke.
- [notebooks/08_qwen3_hybrid_kaggle_memory.ipynb](../notebooks/08_qwen3_hybrid_kaggle_memory.ipynb) — [Memory profiling entry point] Loads the separately checksummed telemetry package in a fresh Kaggle session and retains scalar stage-memory evidence.
- [docs/KAGGLE_MEMORY_PROFILE.md](KAGGLE_MEMORY_PROFILE.md) — [Profiling protocol] Documents the confirmed OOM, excluded logits hypothesis and manual smoke/measurement gates without claiming a memory fix.

## Professor meeting preparation — 4 November 2026

- [docs/PROFESSOR_MEETING_2026-11-04.md](PROFESSOR_MEETING_2026-11-04.md) — Meeting brief with four evidence rows, verified source links, a proposed API pilot and manual/automated workflow; use for the November professor discussion.
- [docs/CITATION_REVIEW_2026-11-04.md](CITATION_REVIEW_2026-11-04.md) — Primary-source metadata corrections for the proposal/report references, including the malformed workspace author list; use when updating the bibliography.
- [docs/validation/2026-11-04_clean_source_transcript.md](../docs/validation/2026-11-04_clean_source_transcript.md) — Verbatim generated reasoning/actions and actual Docker results from the audited clean release, with provenance; retain as meeting evidence.
- [docs/validation/2026-11-04_ten_error_transcript.md](../docs/validation/2026-11-04_ten_error_transcript.md) — Verbatim generated reasoning/actions and actual Docker results from the acknowledged ten-error failure; retain without repairing model mistakes.
- [docs/validation/2026-11-04_meeting_evidence.json](../docs/validation/2026-11-04_meeting_evidence.json) — Machine-readable extraction of task outcomes, source checksums and PDF-correction checks; retain for meeting-claim verification.
- [docs/validation/2026-11-04_reproduction_references_corrected.pdf](../docs/validation/2026-11-04_reproduction_references_corrected.pdf) — Copy of the submitted report with reference page 6 replaced using verified metadata; retain alongside citation-review notes without treating the report body as newly validated.

## API evaluation preparation — 4 November 2026

- [docs/API_EVALUATION_PREPARATION.md](API_EVALUATION_PREPARATION.md) — Current evidence audit, primary-source model/provider verification and proposed host API/Docker logging and replay contract; use before implementing or authorizing the new evaluation workflow.

- [docs/GEMMA_API_IMPLEMENTATION_PLAN.md](GEMMA_API_IMPLEMENTATION_PLAN.md) — Detailed Gemma/full-258-error implementation sequence, provider/key investigation, cost scenarios, evidence schema and repository layout; review before implementing or authorizing live API trials.

## API implementation — 4 November 2026

- [src/api_eval/__init__.py](../src/api_eval/__init__.py) — Marks the separate host API evaluation package; retain with the new runner.
- [src/api_eval/records.py](../src/api_eval/records.py) — Validates frozen conditions and native tool envelopes without repairing commands; use before dispatching API actions.
- [src/api_eval/evidence.py](../src/api_eval/evidence.py) — Publishes exclusive durable run records, exposed reasoning artifacts and final hashes; use for interrupted and completed API evidence.
- [src/api_eval/provider.py](../src/api_eval/provider.py) — Captures exact credential-free HTTP bodies/chunks and safe metadata without retries; use for the candidate API endpoint.
- [src/api_eval/campaign.py](../src/api_eval/campaign.py) — Locks and persists cross-run estimated spend reservations including unknown charges; retain with API budget control.
- [src/api_eval/container_rpc.py](../src/api_eval/container_rpc.py) — Executes task shells as dev and exposes trusted bounded inventory/control operations inside Docker; needed by generated API images.
- [src/api_eval/docker_task.py](../src/api_eval/docker_task.py) — Controls setup-only task containers with argv/stdin RPC, workspace snapshots and cleanup; use from the Mac controller.
- [src/api_eval/runner.py](../src/api_eval/runner.py) — Runs bounded native action/result exchanges with conservative context accounting and optional request pacing, preserving assistant continuation fields and actual observations; use for API rollouts.
- [src/api_eval/verify_precommit.py](../src/api_eval/verify_precommit.py) — Orchestrates protected full-258-source baseline and submitted-hook checks with explicit human-review limits; validate live before task claims.
- [src/api_eval/validate_run.py](../src/api_eval/validate_run.py) — Checks run hashes, event order and saved result/history consistency; use when inspecting or backing up API evidence.
- [scripts/prepare_api_environment.py](../scripts/prepare_api_environment.py) — Generates a setup-only API Docker copy and provenance patch from unchanged upstream sources; use before image builds.
- [scripts/run_precommit_api.py](../scripts/run_precommit_api.py) — Provides prepare-only, Docker preflight, explicit capability and task launch modes with live-call gates; use for new Gemma runs.
- [scripts/inspect_api_run.py](../scripts/inspect_api_run.py) — Reports API evidence integrity and incomplete-JSON problems offline without resuming any command or inference; use after preparation or runs.
- [configs/precommit_hook_gemma4_12b_api_v1.json](../configs/precommit_hook_gemma4_12b_api_v1.json) — Defines the candidate Gemma/full-258 API condition with unresolved billing/readiness gates; resolve only after provider review.
- [tests/test_api_eval.py](../tests/test_api_eval.py) — Tests raw capture, strict protocol, failure retention, budget reservations and preparation without live APIs or Docker; run after API changes.
- [docs/API_RUN_GUIDE.md](API_RUN_GUIDE.md) — Documents implemented API commands, local credential handling, operational gates and current validation limits; consult before launching.
- [docs/API_LOG_SCHEMA.md](API_LOG_SCHEMA.md) — Defines the v1 raw evidence layout, usage/exposure limits and integrity checks; retain for reconstruction and schema review.
- [docs/API_ANNOTATION_RUBRIC.md](API_ANNOTATION_RUBRIC.md) — Separates task/report/reasoning labels and required cited evidence without inferring hidden intent; use for post-run review.

- [scripts/check_gemma_api.py](../scripts/check_gemma_api.py) — Runs one explicitly authorized arithmetic, thinking-control or tool-format-only API evidence check from a literal root .env credential without Docker or fabricated results; use to establish endpoint access before task rollout.
- [tests/test_api_smoke.py](../tests/test_api_smoke.py) — Checks literal credential loading, duplicate-key rejection, arithmetic/tool flows and partial/native reasoning capture without real keys or network; run after smoke-loader changes.

- [configs/precommit_hook_gemma4_12b_api_258_v1.json](../configs/precommit_hook_gemma4_12b_api_258_v1.json) — Freezes the authorized original-258-error Gemma condition with tested thinking controls, bounded autonomous limits and a $1 estimated campaign ceiling; retain separately from the earlier unresolved candidate.

- [configs/precommit_hook_gemma4_12b_api_258_paced_v1.json](../configs/precommit_hook_gemma4_12b_api_258_paced_v1.json) — Authorized fresh follow-up after the provider TPM interruption, with 65-second request pacing and a 60-call cap; retain to reproduce the separately recorded paced condition, which later ended in an API transport timeout.

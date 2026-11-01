# Manual Kaggle inference / Mac Docker protocol

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

Prepared 1 November 2026; offline-tested preparation, not a live Kaggle result. Researcher authorized switching inference after Colab GPU quota exhaustion. No Kaggle account operation, GPU session, model generation, paid purchase or task run was performed during preparation.

## What changes

Docker/controller/verifier stay on the Mac. The model stays Qwen/Qwen3-4B, pinned revision 1cfa9a7208912126459214e8b04321603b3df60c, in native thinking mode. Prompts, sampler, source_10, twelve-call/90-minute cap and 4096 thinking/1024 JSON/16384 context-token limits match the prepared Colab small-source condition. Only protocol/platform metadata changes in configs/precommit_hook_qwen3_hybrid_small_kaggle.json. Runtime libraries, GPU/kernel implementation and storage can differ and are recorded; do not pool platforms or assume identical sampled trajectories.

Notebook 07 replaces google.colab upload/download and Drive mounting with a private Kaggle package input, safely encoded copy/paste request cells, working-files downloads and explicit evidence backups. Inference remains on GPU 0 even if Kaggle exposes two GPUs: no automatic memory pooling, sharding or speedup. This migration supplies another GPU allocation, not proof of a stronger model or better task competence.

The interrupted results/qwen3_hybrid_small_release_01/ must remain preserved. It had a verified ten-error baseline but no model response or command execution before Colab became unavailable. It now has an incomplete controller record and must not be resumed. Never generate/import its old pending request 651d8c9f6be24630a57c0fb62883de45. Use a fresh Kaggle-labeled Mac run after setup.

## 1. Account/GPU check — first manual action

1. Create/open a PRIVATE Kaggle notebook. Complete account/phone verification if Kaggle requires it for accelerator or Internet access.
2. Import notebooks/07_qwen3_hybrid_kaggle_mac.ipynb. Select an available GPU accelerator in notebook settings (prefer T4 x2 to retain the GPU family) and enable Internet for package/model downloads. Check your displayed GPU quota; this is another quota-limited service, not guaranteed access.
3. Run only the first code cell. It must show CUDA available and actual GPU names. It uses only GPU 0. If no GPU is available, stop before installing/loading anything. Report a different GPU/runtime as a platform difference.

Do not start a Mac controller yet. The live Kaggle accelerator selector and frontend are not validated by our offline tests. Current official announcements retire P100; do not assume every old guide's hardware list still applies.

## 2. Private package input and download check

Attach work/qwen3_hybrid_kaggle_20261101.zip as a PRIVATE notebook input. In Kaggle's Add Input/data UI, upload the package into a private dataset/input and attach it; do not publish the notebook, source or reasoning records. Dataset/input creation is a user action, not performed by the assistant. The package is small and contains allowlisted code/config/docs only, no weights, secrets or historical run evidence.

Kaggle may keep the ZIP or expand it. The setup cell finds either the exact archive name or a unique expanded PACKAGE_MANIFEST.json beside the Kaggle-specific config. It checks every source hash before copying only declared files into /kaggle/working/capstone/ai-safety-capstone. Existing matching packages are verified and reused; mismatched/partial contents are never silently overlaid. It rejects unsafe paths and links. If multiple inputs match, remove the stale notebook attachment rather than selecting an arbitrary one.

Run the setup cell. If the ZIP is preserved, compare its printed archive SHA256 with work/qwen3_hybrid_kaggle_20261101.zip.sha256. If Kaggle expanded it, an archive hash is unavailable: the cell reports that mode and the original manifest hash; source hashes still validate. Compare manifest identity with work/qwen3_hybrid_kaggle_20261101.source_manifest.json on Mac. Dependency installation keeps the existing broad Torch requirement and pins Transformers 4.57.1/LMFE 0.11.3; actual versions are recorded. Do not install a CPU Torch wheel to solve a missing accelerator.

Download the small kaggle_transfer_check.json file displayed by the cell BEFORE loading the model. A standard file link is provided; if Kaggle's frontend does not serve it, use its working-files/output browser and navigate to the printed path. This is a required live transport check, not model evidence. If you cannot download it, stop for UI diagnosis rather than starting a task.

## 3. Model load and one platform smoke

Run the model-load cell. It verifies atomic hard-link support for the local spool, pinned checkpoint/template, native thinking mode and actual GPU/runtime metadata. It records platform=kaggle_manual_v1, visible devices and active GPU 0. It must not run twice in one kernel with an existing engine; do not load both old and new checkpoints. The model download is approximately 8 GB. GPU time is consumed while the session is active, including manual waits.

The cell creates session evidence under:

/kaggle/working/capstone/ai-safety-capstone/results/kaggle_<UTC timestamp>/

This is working/session storage, NOT a persistent mounted Drive. Do not assume notebook autosave retains these files. Download each completed bundle promptly, and download the evidence backup before ending a session. Saving versions/outputs must not rerun generations: avoid Save & Run All.

Run the helper-definition cell (no generation), then the single neutral arithmetic smoke once. Require naturally closed, nonempty thinking, a correct constrained final_report and passing P0/R1 replay at all three selected layers. Download its bundle and share the output. A platform smoke pass is not a full task result. On error, incomplete thinking, OOM or replay failure, preserve/download records and stop. Do not repeat the old Docker diagnostic campaign.

## 4. Fresh ten-error task on Mac

Only after the platform smoke and download check pass, start Terminal A from the repository root:

```sh
cd /Users/aknurabdikarim/Documents/ai-safety-capstone
python3 scripts/run_precommit_qwen.py --config configs/precommit_hook_qwen3_hybrid_small_kaggle.json --manual --container-timeout 5400 --run-dir results/qwen3_hybrid_small_kaggle_01
```

This builds current host code and runs actual reference-hook controls, including staged-only detection, plus the ten-error baseline. Wait for Starting task controller. If any preflight fails, stop and inspect logs; no request should be generated. See SMALL_FAILING_SOURCE_RUN.md for exact verification scope, annotation-quality review and limitations. This is a small failing-source pre-commit experiment, not the original 258-error arm.

Terminal B exports the first request:

```sh
python3 scripts/manual_exchange.py export --run-dir results/qwen3_hybrid_small_kaggle_01 --file results/qwen3_hybrid_small_kaggle_01/small_call_01.request.json
mkdir -p results/qwen3_hybrid_small_kaggle_01/downloads
```

Generate the safely quoted notebook cell and put it on the Mac clipboard:

```sh
python3 scripts/kaggle_request_cell.py --run-dir results/qwen3_hybrid_small_kaggle_01 --request results/qwen3_hybrid_small_kaggle_01/small_call_01.request.json | pbcopy
```

The helper verifies the exported file still matches the pending request and emits only a Python cell containing a quoted JSON DATA literal plus a call to evaluate_and_save. It does not generate, execute a shell command or contact a service. Python repr quoting prevents request text from becoming executable code. If it reports an error, do not paste stale clipboard contents. Do not manually embed raw JSON inside quotes.

Paste the COMPLETE clipboard contents into the designated new Kaggle code cell and run once. Compare call IDs. Download CALL.response_bundle.json using its link or working-files browser. On Mac, replace CALL with the printed ID and actual downloaded filename:

```sh
cp ~/Downloads/CALL.response_bundle.json results/qwen3_hybrid_small_kaggle_01/downloads/
python3 scripts/manual_exchange.py import --run-dir results/qwen3_hybrid_small_kaggle_01 --file results/qwen3_hybrid_small_kaggle_01/downloads/CALL.response_bundle.json
```

Import releases the validated command to the disposable Docker workspace. Never run a generated command in the capstone repository. Then export the next pending request using small_call_02.request.json, run the same clipboard helper with that file, paste into a new Kaggle cell, generate once and import its downloaded bundle. This replaces per-call Colab file uploads; there is no server, tunnel, hosted API or automated transport.

No coaching, request editing, output repair or synthetic tool results. A failed shell command is actual feedback and does not necessarily end a rollout. Stop on the first technical failure or declared limit, preserve/import error bundles to terminate the waiting controller where appropriate. Do not bypass a claimed-call guard or regenerate after a disconnect without checking records. After final_report, import the last bundle and let the controller/export/verifier finish; do not export another request.

## 5. Retention, audit and shutdown

- Mac results/qwen3_hybrid_small_kaggle_01/ retains launch/config/source/build logs, bridge requests/results, full bundles, checkpoints, protected submission and independent verifier JSON. It is Git-ignored; back up separately.
- Kaggle session results/ retains package/config/runtime metadata and per-phase request/input/reasoning/token/vector/replay/response artifacts before complete bundle creation. They are not guaranteed durable across runtime loss.
- Run the final evidence-backup cell after completed calls and before shutdown; download its ZIP and checksum. It archives only the session evidence folder, not model weights. Save/download the executed notebook without re-executing calls. Copy backup files into the matching Mac run's archive/ folder.
- Review verification/small_release_reference_checks.json and small_release_checks.json, full transcript, source diff, hook behavior and final claims before assigning an outcome. Counterfactual verifier fixtures are not model behavior. P0/R1 are engineering extraction positions, not original report-content P1. No valid probe study follows automatically.
- Stop the Kaggle session when done to avoid spending quota while idle. A quota loss is an infrastructure interruption, not evidence of deception or coding inability. No paid GPU provisioning or larger experiment is automatic.

## Preparation evidence and sources

75 offline tests passed, including safely quoted hostile/multiline request data, pending-request checks, ZIP/expanded-input verification, traversal/link rejection and mismatch-safe reuse. GPU allocation, Kaggle UI downloads, dependency compatibility and generation/replay are untested live gates. Original upstream sources remain checksum-verified; no new model/Docker/Kaggle trial occurred in preparation.

Sources: [Kaggle notebook documentation](https://www.kaggle.com/docs/notebooks), [official notebook environment repository](https://github.com/Kaggle/docker-python), [NVIDIA Kaggle setup guide](https://docs.nvidia.com/datascience/deployment/26.10/platforms/kaggle/index.html), [Kaggle P100 retirement announcement](https://www.kaggle.com/discussions/product-announcements/735239). Where UI behavior is uncertain, the explicit file-transfer check is the authority; do not claim our live compatibility from documentation alone.

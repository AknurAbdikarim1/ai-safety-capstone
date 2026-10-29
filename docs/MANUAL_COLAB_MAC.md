# First manual Colab–Mac test

**29 October 2026:** the instructions below describe the historical XML/full-task workflow. For the current bounded serial diagnostic condition, use [SERIAL_DIAGNOSTICS.md](SERIAL_DIAGNOSTICS.md) and notebook 04. Do not launch the full task as a formatting test.

Qwen inference runs interactively in Colab; the original task runs inside Docker Desktop on your Mac. There is no notebook-hosted server or remote-control tunnel. Keep the Mac controller alive while transferring files. No model-generated command runs on the host or Colab.

## 1. Check Docker on your Mac

Open Docker Desktop and wait for it to start. In a Mac terminal:

```sh
docker info --format '{{.OSType}} {{.Architecture}}'
```

Expected: Linux and the container architecture. The researcher verified `linux aarch64` on their Mac and successfully built the image. Runtime checks confirmed adapter imports, mypy 1.20.2, non-root command execution and protected controller files. These results were shared in chat; the assistant session itself remains blocked from the Docker socket.

## 2. Prepare Colab before starting the controller

Open `notebooks/03_manual_colab_mac.ipynb`, select a GPU runtime, upload the updated repository ZIP, install requirements, mount Drive and load Qwen. No Docker installation in Colab is needed. The notebook saves each complete response bundle to Drive. Its temporary generation queue stays on /content, where atomic local-file operations work.

## 3. Start one capped task attempt on your Mac

From the repository root, in Terminal A:

```sh
python3 scripts/run_precommit_qwen.py --manual --run-dir results/manual_01
```

This prepares and builds the image, launches the controller, and waits for manually imported generation responses. The initial mode allows at most five model calls, 30 minutes waiting per call, and three hours for the container. A limit stop is incomplete, not task failure/deception. The CLI writes original and overridden settings to config.json. First image build may download dependencies. The researcher has already completed a successful build of the current image on their Mac.

No separate hosted worker runs on your Mac. Keep Terminal A running. Do not rerun the launcher with the same directory or execute its container twice. You may use `--prepare-only` together with `--manual` to inspect the build/config without launching, but the normal launcher will then require a different new run directory. That prepare-only output is for inspection, not a resume command.

## 4. Transfer one request, then return one response

In Terminal B, inspect whether a request is pending:

```sh
python3 scripts/manual_exchange.py status --run-dir results/manual_01
```

If none exists, the image may still be building, the controller may have ended, or an error occurred. Inspect Terminal A and `results/manual_01/controller.log` when present.

Export the first pending request:

```sh
python3 scripts/manual_exchange.py export --run-dir results/manual_01 --file work/request_01.json
```

Upload that file using the repeat-turn cell in Colab. Execute the generation cell once and download its `CALL.response_bundle.json`. Then import the downloaded file on your Mac:

```sh
python3 scripts/manual_exchange.py import --run-dir results/manual_01 --file /absolute/path/to/CALL.response_bundle.json
```

The importer checks request identity/hash, token-record consistency and parsed text, saves the raw evidence, and publishes the response last. Only then does the controller execute any tool action inside Docker. This assumes files are transferred unchanged and are your own generated records; hashes are not proof of model identity or protection against deliberate record fabrication.

Repeat status/export/upload/generate/download/import with a fresh export filename (`work/request_02.json`, etc.). Every request already contains the latest tool results. Duplicate, stale or mismatched responses are rejected; no command is run by the transfer CLI itself.

## 5. End and review

The controller exits after a report, error, or turn cap. Inspect `controller.log`, `controller_status.json`, `controller/` checkpoints/checks and `bridge/` records. Colab response bundles contain the exact tokens as well as raw generated text and are saved to Drive and imported back into the Mac run directory.

A malformed/truncated generation is returned as an error bundle so the controller can stop explicitly. Missing reasoning is not assigned to the negative group. No explicit reasoning-elicitation prompt was added. This test establishes the transfer/execution path, not deception prevalence, task generalization, or validated CoT.

Do not automatically resume after timeout/disconnection: a shell action may have occurred before a checkpoint. First check saved bundles and tool-result records. After a Colab restart, recover an existing Drive bundle before deciding to generate a pending request again.

## Status

As of 27 October 2026, all 23 offline tests pass and all 101 upstream files match their source checksums. The researcher verified Docker/reference-hook checks and constrained Qwen inspection exchanges. These establish interface functionality under diagnostic instructions; autonomous full-task reliability remains unverified.

## Bundle storage

Colab downloads go to the location selected by your browser, normally Downloads. After a validated import, the Mac importer also keeps the complete bundle at `results/<run-name>/bundles/<call-id>.response_bundle.json`; detailed request/token/tool records remain in `bridge/`. These runtime artifacts are Git-ignored, so back them up separately. Importing publishes the response and may execute its tool call in Docker; inspect the response before importing rather than using import solely as a file-copy command. Existing bundles are never overwritten with different evidence.

## Fresh full-task attempt after interface review — 27 October 2026

Historical procedure: this attempt has now ended at step 0 with a tool-protocol error; no model-generated commands executed. Preserve `results/full_task_01` and do not rerun these commands with that directory. That proposed next evaluation was superseded by the local serial adaptation; use `SERIAL_DIAGNOSTICS.md`. This is not Qwen-Agent execution.

The review found a history-format bug: the controller stores function arguments as JSON strings, but the saved Qwen template applies JSON serialization itself. The inference adapter now converts historical arguments to objects on a copy before rendering; the request hash, raw output and strict parser are unchanged. New model metadata records `tool_history_format: object_arguments_v1`. This affects turns after a tool call and cannot explain malformed first-turn responses. The cached template hash matches the saved file-inspection input record; its rendering was checked before and after correction.

Use a fresh copy of `notebooks/03_manual_colab_mac.ipynb` in a restarted Colab runtime, with the updated `work/colab_full_task_01.zip` prepared on the Mac; keep executed diagnostic notebooks as evidence. Run the setup, Drive and model-loading cells. Confirm `engine.metadata.get('tool_history_format') == 'object_arguments_v1'` before starting Docker. No diagnostic cells or extra task instructions are used. The notebook's baseline generation settings match the reminder condition exactly.

Terminal A, from the repository root:

```sh
python3 scripts/run_precommit_qwen.py \
  --config configs/precommit_hook_qwen_format_reminder.json \
  --manual \
  --run-dir results/full_task_01
```

This presents the complete original task plus the existing neutral formatting reminder, with five model calls, 30 minutes per response and three hours for the container. It does not guarantee enough turns to complete the task; reaching the cap means incomplete. Do not use the diagnostic configuration or reuse an existing run directory.

Terminal B, after a request appears:

```sh
python3 scripts/manual_exchange.py export \
  --run-dir results/full_task_01 \
  --file work/full_task_request_01.json
```

Upload that request in the notebook's repeat-turn cell, generate once, download the bundle, inspect it, and import the exact downloaded path with `scripts/manual_exchange.py import --run-dir results/full_task_01 --file /absolute/path/to/CALL.response_bundle.json`. Import an error bundle too to record the failure and release the waiting controller; do not repair its output. For each subsequent pending call, use a new export filename and repeat. Do not send another request after the controller stops.

Stop this attempt on protocol error, truncation, timeout, report or the five-call cap. Preserve every bundle and inspect the controller records and outcome checks. Successful tool formatting alone is not task success; a final claim needs comparison with actual repository/check evidence. Since generation is greedy and the first prompt is unchanged, repeating the earlier first-turn failure is plausible; this is a confirmation attempt, not an independent behavioral sample. Do not start further attempts or add prompt instructions automatically.

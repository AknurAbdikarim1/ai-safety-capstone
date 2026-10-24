# First manual Colab–Mac test

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

All 19 offline tests pass. The researcher also reported successful Docker build/runtime checks, 258 errors for `src_258`, a clean `src_0`, and a reference Git hook that blocks the failing source and permits the corrected source. No Qwen-driven manual exchange has run yet. All original upstream files remain unchanged. Next gate: load Qwen in Colab and validate one file-transfer round trip before the capped task attempt.

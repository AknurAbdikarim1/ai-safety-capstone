# AI safety capstone — milestone 1

The current research roadmap is [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md). It adopts observed explicit-deception-evidence versus other-misleading-report grouping, superseding the original evidence-condition A/B proposal. The implementation below remains the initial smoke test.

Minimal Qwen2.5-3B-Instruct inference and activation extraction. No synthetic dataset, condition manipulation, probe training, or fine-tuning is implemented yet.

## Setup and local run

Use Python 3.10–3.12. Open this folder in VS Code. In a terminal:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/run_model.py --device cuda --output-dir results/smoke_001
```

For a machine without CUDA, pass `--device cpu`; this uses float32 and can be slow and memory intensive. The recommended first execution is Colab. The first run downloads model weights from Hugging Face into its cache. No API key or paid API is used. CUDA uses float16, without quantization. Model weights alone are roughly 6 GB at this precision; runtime memory is higher. Availability and capacity of free cloud GPUs vary.

## Colab

1. Upload `notebooks/01_model_setup.ipynb` to Colab.
2. Choose Runtime → Change runtime type → T4 GPU (or another available GPU).
3. Execute cells in order and upload the supplied `ai-safety-capstone.zip` when requested.
4. Install dependencies, check CUDA, and mount Google Drive.
5. Run the script. Outputs go directly into a unique folder under `MyDrive/ai-safety-capstone/`.
6. Confirm that all three arrays load, have shape `(1, 2048)`, contain finite numbers, and that a generated response and metadata were saved.

For Kaggle, enable GPU and Internet, upload/extract the ZIP, install requirements and run the same script with `--output-dir /kaggle/working/smoke_001`. Save a notebook version with outputs and download those outputs before ending the runtime.

## What is measured

The default selected decoder blocks are **9, 18 and 27**, numbered from 1. This is a small, spaced selection for a technical smoke test, not a research-optimized layer choice. Each hook captures the block output residual stream at the **last token of the complete chat-formatted input**, including its assistant generation prefix. Its exact index, decoded token and all input IDs are saved. This token can be a formatting token rather than the final word of the user's question.

Extraction uses a separate prompt-only forward pass, before response generation. Hooks copy only `[batch, last_position, hidden_size]` to CPU as float32 arrays of shape `(1, 2048)`. They do not request or retain all layers' hidden states. Hooks are removed before greedy generation. These are decoder block outputs **before the model's final RMSNorm**, including for layer 36 if explicitly selected; they are not the final normalized `hidden_states[-1]`. One unpadded example is processed per run.

Every selected layer is saved as `smoke_001_layer_XX.npy`, with task association in `metadata.json`. The script validates shape, finiteness and save/load equality. Metadata records the actual generated response, prompt, model revision, layers, generation options, precision, seed, hardware and installed package versions. Seeds do not guarantee bitwise agreement across hardware. Use `--revision COMMIT_SHA` with the recorded resolved revision for future runs. Requirements constrain the environment; record and compare actual installed versions before research runs.

New smoke runs also record elapsed seconds and peak GPU allocated/reserved bytes in `metadata.json` under `measurements`. Timing covers seed setup, tokenizer/model loading (including downloads if needed), extraction, generation, and decoding; it excludes imports and output saving. CUDA is synchronized at the measurement boundaries. Memory peaks cover PyTorch's CUDA allocator in the script process, not total device usage. The notebook displays these fields when present and still loads older runs without them. Cached model files can reduce loading time, so elapsed times across runs may differ.

## Repository and GitHub

This folder is initialized as a local Git repository. A GitHub repository has not been created or linked. After creating an empty repository named `ai-safety-capstone` in your own account, run:

```sh
git add .
git commit -m "Add Qwen activation smoke test"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-safety-capstone.git
git push -u origin main
```

Do not add a second remote if one already exists. Review `git status` before committing. Weights, caches, secrets, activations and generated results are ignored. `data/`, `activations/` and `results/` are placeholders. Reusable code lives in `src/`; the notebook only handles setup and execution.

## Validation status and next gate

Local checks cover Python syntax, notebook structure and archive contents. **Full model loading, inference and activation extraction have not yet been executed on a GPU.** The milestone is complete only after the Colab smoke test succeeds and its saved arrays and response are inspected. Preserve that run's metadata and dependency versions before expanding the pipeline.

The arithmetic prompt is a technical check, not a misleading-report experiment. Next, review a 5–10 template behavioral pilot before implementing it. Research labels will describe observed evidence in model rollouts, not established intentions or beliefs; see the current roadmap for the revised annotation design. Comparable misleading outputs must be observed rather than assumed. High condition accuracy can reflect prompt wording; even outperforming a particular text baseline would not by itself establish deception or a distinct psychological mechanism.

Model loading follows the [official Qwen model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) and [Qwen Transformers guidance](https://qwen.readthedocs.io/en/v2.5/inference/chat.html).

## Original Pre-commit Hook source

The exact upstream task and supporting framework files are preserved under `experiment_sources/agent-interp-envs/`. See [the adaptation checklist](docs/PRECOMMIT_ADAPTATION.md) and `experiment_sources/UPSTREAM_MANIFEST.json` for pinned checksums. Run `python3 scripts/verify_upstream.py` to verify source integrity. Adaptations patch generated copies beneath ignored `work/`; originals remain unchanged.

## Current API workflow

The Mac-controlled API runner is `scripts/run_precommit_api.py`, implemented in `src/api_eval/`. The initial candidate is Gemma 4 12B Instruct on the original 258-error task. Configuration is `configs/precommit_hook_gemma4_12b_api_v1.json`; provider capabilities, reasoning scope and spending limits must be resolved before live calls. No GPU or model weights are required on the Mac. Python 3.10+ and Docker Desktop are required for container runs.

Start without a key or Docker:

```sh
python3 scripts/run_precommit_api.py --prepare-only --run-dir results/gemma4_api_prepare_001
python3 scripts/inspect_api_run.py results/gemma4_api_prepare_001
```

After starting Docker Desktop, run the no-API container/checker gate:

```sh
python3 scripts/run_precommit_api.py --preflight --run-dir results/gemma4_api_preflight_001
```

Every run directory must be new. Runtime evidence stays under ignored `results/` and requires a separate backup. A prepared or normally terminated run is not automatically a successful task. The new image/checker and provider exchanges still require live validation; see [the research log](docs/RESEARCH_LOG.md) for actual checks and limitations.

Keep the API key in the repository-root `.env` as `SILICONFLOW_API_KEY=your_actual_key`, never in tracked config or chat. `.env` is ignored. Restrict it and load the named variable in your local shell before an authorized live run:

```sh
chmod 600 .env
source .env
export SILICONFLOW_API_KEY
```

Only source your own trusted local file. The runner reads this environment variable and does not auto-load `.env`; the key is never forwarded into the task container. Paid calls require explicit `--allow-paid-api`, resolved billing and a shared campaign ledger. A full task also requires capability review and resolved reasoning policy; do not set readiness true merely to bypass these checks.

## Historical Qwen workflow

[QWEN_INTEGRATION.md](docs/QWEN_INTEGRATION.md) and [MANUAL_COLAB_MAC.md](docs/MANUAL_COLAB_MAC.md) document the older notebook/container and manual-transfer setup. Saved evidence includes an audited clean-source release and incomplete ten-error attempts, including a later GPU OOM. These runs do not establish full-258-error competence, a qualifying deception dataset or trained probes. The API workflow supersedes manual-transfer next steps; preserve old code/evidence for provenance.

# Research log

This file records actions, results, and learnings. Add entries as work continues. Results from Colab below were shared by the researcher in chat; the saved files have not been inspected locally.

## 2026-10-22 — Repository review

**Action**
- Read the research plan, README, model script, notebook, requirements, and Git setup.
- Checked Python syntax and notebook JSON.

**Result**
- Syntax and JSON checks passed.
- The repo contains an inference and activation smoke test.
- Task collection, checkers, annotation, replay validation, and probe training are not implemented.
- No model run had been recorded at the time of review.

**Learning**
- The next step was to verify model inference and activation storage on a GPU.
- The arithmetic prompt checks the pipeline. It does not test misleading reports or deception.
- The research labels describe evidence in written traces, not proven intent.

## 2026-10-22 — GitHub setup

**Action**
- Created a private repo: https://github.com/AknurAbdikarim1/ai-safety-capstone
- Added `.DS_Store` to `.gitignore`.
- Committed the project and pushed `main` to GitHub.

**Result**
- Initial commit: `e18a7cd` — `Add Qwen activation smoke test and research plan`.
- Verified that the repo is private and `main` tracks `origin/main`.

**Learning**
- The GitHub CLI can create and push the repo from the terminal.
- A ZIP used in Colab can come from the local folder or GitHub. It should contain the version intended for the run.

## 2026-10-22 — Notebook review and update

**Action**
- Updated `notebooks/01_model_setup.ipynb`.
- Replaced the fixed project path with detection of the project folder inside the uploaded ZIP.
- Added checks for all three default layers, array shape, dtype, and finite values.
- Added instructions for reloading outputs after a runtime restart.
- Checked notebook JSON, Python syntax outside notebook magic commands, and diff whitespace.
- Explained the notebook code line by line.

**Result**
- Checks passed. Colab execution was still needed at this point.
- Commit: `53fa6fa` — `Simplify Colab setup and validate saved smoke outputs`.
- This commit has not been pushed to GitHub as of this entry.

**Learning**
- The notebook handles setup and inspection; the model code stays in `src/run_model.py`.
- The notebook accepts a project ZIP with a different root-folder name, including GitHub's `ai-safety-capstone-main`.

## 2026-10-22 — Colab setup

**Action**
- Selected Python 3, T4 GPU, and the latest runtime in Colab.
- Uploaded `ai-safety-capstone.zip` from the local project folder.
- Ran the upload and extraction cell.
- Installed `requirements.txt` and checked CUDA access.

**Result**
- Project directory: `/content/ai-safety-capstone`.
- GPU: `Tesla T4`.
- Package versions shown in the installation output:
  - Python: 3.13, based on the package path.
  - PyTorch: `2.11.0+cu130`.
  - Transformers: `4.57.1`.
  - Accelerate: `1.15.0`.
  - NumPy: `2.1.3`.
  - Hugging Face Hub: `0.36.2`.
  - Tokenizers: `0.22.2`.
- Pip reported dependency conflicts with Colab's installed Diffusers, Gradio, and Gradio Client packages. Installation finished, and the GPU check passed.

**Learning**
- Installing packages and detecting a GPU do not verify model loading.
- The smoke script does not use the packages named in those conflict warnings. The later model run passed in this environment.
- The README recommends Python 3.10–3.12, but this run used Python 3.13. Record the environment that actually ran.

## 2026-10-22 — Drive storage

**Action**
- Mounted Google Drive and chose a timestamped run folder.

**Result**
- Drive mounted at `/content/drive`.
- Run folder:

```text
/content/drive/MyDrive/ai-safety-capstone/smoke_20261022T142501425033Z
```

**Learning**
- Outputs are saved to Drive so they can be loaded after the Colab runtime ends.
- Each model run needs a new output folder. The script rejects a nonempty output folder.

## 2026-10-22 — First Qwen GPU run

**Action**
- Ran `src/run_model.py` on CUDA with the Drive output folder.
- Used the default prompt: `What is 17 + 25? Answer briefly.`
- Used the default layers: 9, 18, and 27.
- Ran the notebook's saved-output inspection cell.

**Result**
- Script return code: `0`.
- Model: `Qwen/Qwen2.5-3B-Instruct`.
- Model revision: `aa8e72537993ba99e69dfaafa59ed015b17504d1`.
- Response: `42`.

| Layer | Saved shape | Saved dtype | Finite values |
| --- | --- | --- | --- |
| 9 | `(1, 2048)` | `float32` | Passed |
| 18 | `(1, 2048)` | `float32` | Passed |
| 27 | `(1, 2048)` | `float32` | Passed |

- The script's shape, finiteness, and save/reload equality checks passed.
- The notebook loaded the saved arrays and metadata from Drive in the same runtime.
- Reported filenames are defined by the script: `smoke_001_layer_09.npy`, `smoke_001_layer_18.npy`, `smoke_001_layer_27.npy`, and `metadata.json`.

**Learning**
- Qwen inference and activation extraction ran on the T4 in this environment.
- Each array holds the selected block's output at the last input token: one example and 2,048 values.
- The model uses float16 on CUDA; the script converts the saved vectors to float32. This conversion does not add precision to the model computation.
- The vectors come from a prompt-only pass before answer generation. They do not contain generated answer tokens.
- These results verify the smoke run. They provide no evidence about deception detection.

## 2026-10-22 — Reload after runtime restart

**Action**
- After the restart step, mounted Drive and set `run_dir` to the saved run folder.
- Reran the output inspection cell without rerunning model generation.

**Result**
- Layers 9, 18, and 27 loaded with shape `(1, 2048)`, dtype `float32`, and finite values.
- Saved response: `42`.
- Saved model revision: `aa8e72537993ba99e69dfaafa59ed015b17504d1`.
- The researcher shared the output in chat.

**Learning**
- The saved arrays and metadata can be loaded from Drive after the restart step without loading Qwen or generating another answer.

## 2026-10-22 — Add runtime and memory tracking

**Action**
- Added elapsed time and peak GPU allocated/reserved bytes to the script's metadata and printed output.
- Added CUDA synchronization at the measurement boundaries and reset peak counters before model loading.
- Updated the setup notebook to display measurements and still load older runs without them.

**Result**
- Code changes are saved locally. A Colab run with these changes is pending.
- Timing covers seed setup, loading, extraction, generation, and decoding. It excludes imports and output saving.
- Memory measurements cover PyTorch's CUDA allocator in the script process, not all GPU memory usage.

**Learning**
- Downloads are included in elapsed time when needed; cached weights can make later runs faster.
- Writing measurement code does not complete the measurement check. A new run must produce the values.

## 2026-10-22 — Runtime and GPU memory results

**Action**
- Ran the updated script in Colab and inspected its saved outputs.
- The researcher shared the output in chat.

**Result**
- Layers 9, 18, and 27: shape `(1, 2048)`, dtype `float32`, all values finite.
- Response: `42`.
- Model revision: `aa8e72537993ba99e69dfaafa59ed015b17504d1`.
- Elapsed time: `81.70 seconds`.
- Peak GPU allocated: `5.773 GiB`.
- Peak GPU reserved: `5.869 GiB`.
- Executed notebook: `docs/validation/2026-10-22_smoke_run2.ipynb`. Its saved outputs were inspected locally and match the results above.
- Output path: `/content/drive/MyDrive/ai-safety-capstone/smoke_20261022T150546349901Z`.

**Learning**
- The updated script saved timing and memory measurements, and the notebook read them.
- Elapsed time includes loading and any downloads. It is not generation time alone.
- Allocated memory is memory used by PyTorch tensors; reserved memory includes space held by its allocator for reuse. These values do not measure all GPU usage.
- These measurements apply to this short smoke prompt, not future agent rollouts.
- The [model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) lists about 3.09 billion parameters. At two bytes per float16 parameter, weights require about 5.76 GiB. The measured 5.773 GiB peak allocated is consistent with that estimate; weights appear to account for most memory in this run.
- Peak reserved exceeded peak allocated by about 0.096 GiB. These are separate peaks, not a measurement of unused memory at one instant.
- The [T4 specifications](https://www.nvidia.com/content/dam/en-zz/Solutions/data-center/tesla-t4/t4-tensor-core-datasheet-951643.pdf) list 16 GB of GPU memory. This run fits, but its PyTorch memory figures do not establish how much memory is available for longer tasks.
- For later runs, compare peak memory alongside input token count, generated token count, batch size, and dtype.

## 2026-10-22 — Tokenizer cache check

**Action**
- Used `huggingface_hub.try_to_load_from_cache` in Colab to look up `tokenizer.json` and `tokenizer_config.json` at the recorded model commit.
- The researcher shared the returned paths in chat.

**Result**
- Both files were found under this snapshot:

```text
/root/.cache/huggingface/hub/models--Qwen--Qwen2.5-3B-Instruct/snapshots/aa8e72537993ba99e69dfaafa59ed015b17504d1/
```

**Learning**
- Tokenizer files for the model commit are present in the cache.
- This check does not prove which tokenizer files the earlier runs loaded. The script requested `main` for both model and tokenizer, and did not record a separately resolved tokenizer revision.
- This is a provenance gap. It does not invalidate the observed inference, array checks, or persistence result.
- No extra arithmetic run is needed to repeat those checks. Before research collection, pin both loads to a commit and record their revision provenance. That code change has not been made yet.

## Pending checks and next steps

- Preserve the measured run's metadata in Drive; its output path and executed notebook are now recorded here.
- Step 0.5 has tokenizer cache evidence, with the historical provenance limit recorded above. Do not claim the earlier tokenizer revision was proved. Pin and record revision provenance before research collection.
- Preserve the notebook output and run metadata as evidence for Phase 0.
- Review the remaining Phase 0 requirements before marking the phase complete in `RESEARCH_PLAN.md`.
- After Phase 0, inspect source tasks and draft the pilot protocol and annotation rubric for review. No behavioral collection or probe training has started.

## Entry format for future work

### YYYY-MM-DD — Action name

**Action**
- What was run or changed, including settings and file paths when needed.

**Result**
- Output, checks, failures, and evidence location.

**Learning**
- What the result shows, its limits, and what to do next.

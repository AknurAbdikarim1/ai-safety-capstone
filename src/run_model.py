"""Milestone 1: inference and last-prompt-token residual stream extraction."""
import argparse
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/smoke"))
    parser.add_argument("--layers", type=int, nargs="+", default=[9, 18, 27])
    parser.add_argument("--prompt", default="What is 17 + 25? Answer briefly.")
    parser.add_argument("--revision", default="main", help="Use a model commit SHA for repeat runs.")
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    args = parser.parse_args()
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto":
        device = "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable. Select a GPU runtime or use --device cpu.")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Output directory is nonempty; choose a new directory to preserve previous runs.")
    if device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    started = perf_counter()
    set_seed(args.seed)
    dtype = torch.float16 if device == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=args.revision, torch_dtype=dtype,
        device_map={"": device}, attn_implementation="sdpa",
    ).eval()
    layers = sorted(set(args.layers))
    if not layers or min(layers) < 1 or max(layers) > model.config.num_hidden_layers:
        parser.error(f"Layers must be 1..{model.config.num_hidden_layers} (one-based)")
    messages = [{"role": "user", "content": args.prompt}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(device)
    vectors = {}

    def capture(layer):
        def hook(module, module_inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            # Clone only one token; never keep the full sequence on the GPU.
            vectors[layer] = hidden[:, -1, :].detach().float().cpu().numpy().copy()
        return hook

    handles = []
    try:
        for layer in layers:
            handles.append(model.model.layers[layer - 1].register_forward_hook(capture(layer)))
        with torch.inference_mode():
            # Backbone only: avoids allocating vocabulary logits during extraction.
            model.model(**inputs, use_cache=False, output_hidden_states=False, return_dict=True)
    finally:
        for handle in handles:
            handle.remove()
    with torch.inference_mode():
        generated = model.generate(
            **inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(generated[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    if device == "cuda":
        torch.cuda.synchronize()
    measurements = {
        "elapsed_seconds": perf_counter() - started,
        "scope": "seed setup, tokenizer/model loading (including downloads if needed), prompt processing, activation extraction, generation, and decoding; excludes imports and output saving",
        "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated() if device == "cuda" else None,
        "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved() if device == "cuda" else None,
        "memory_scope": "PyTorch CUDA allocator in this script process; not total GPU usage",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for layer, vector in sorted(vectors.items()):
        expected = (1, model.config.hidden_size)
        if vector.shape != expected or not np.isfinite(vector).all():
            raise RuntimeError(f"Invalid activation at layer {layer}: {vector.shape}")
        filename = f"smoke_001_layer_{layer:02d}.npy"
        np.save(args.output_dir / filename, vector, allow_pickle=False)
        np.testing.assert_array_equal(np.load(args.output_dir / filename, allow_pickle=False), vector)
        print(f"Layer {layer}: {vector.shape}, {vector.dtype} -> {filename}")
        saved[str(layer)] = {"file": filename, "shape": list(vector.shape)}
    metadata = {
        "task_id": "smoke_001", "model_id": MODEL_ID,
        "requested_revision": args.revision, "resolved_revision": getattr(model.config, "_commit_hash", None),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed, "device": device, "model_dtype": str(dtype),
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "measurements": measurements,
        "versions": {name: importlib.metadata.version(name) for name in ["torch", "transformers", "accelerate", "numpy"]},
        "messages": messages, "rendered_prompt": rendered,
        "input_token_ids": inputs.input_ids[0].tolist(),
        "token_position": inputs.input_ids.shape[1] - 1,
        "token_text": tokenizer.decode(inputs.input_ids[0, -1:]),
        "extraction": "prompt processing; decoder block output before final model RMSNorm; one-based layers",
        "activations": saved, "response": response,
        "generation": {"do_sample": False, "max_new_tokens": args.max_new_tokens},
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Response: {response}")
    print(f"Elapsed: {measurements['elapsed_seconds']:.2f} seconds")
    if device == "cuda":
        print(f"Peak GPU allocated: {measurements['peak_gpu_allocated_bytes'] / 1024**3:.3f} GiB")
        print(f"Peak GPU reserved: {measurements['peak_gpu_reserved_bytes'] / 1024**3:.3f} GiB")
    print(f"Saved run: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()

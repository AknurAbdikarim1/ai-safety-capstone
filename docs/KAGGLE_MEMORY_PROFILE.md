# Kaggle stage-memory profiling

Prepared 1 November 2026. The clarified ten-error run ended on call 9 (0a7138643644426e8849b6cd4b8980ce): saved reasoning closes naturally after 124 generated tokens; action generation records CUDA OutOfMemoryError requesting 650 MiB with 348.81 MiB free. Both controller and submission verifier exit 1; invalid appended placeholder declarations leave a syntax error and no release commit. This is separate from earlier coding mistakes; not thinking-cap exhaustion or evidence of deception. Original run records remain unchanged.

## Review and change

The pinned Transformers 4.57.1 GenerationMixin automatically requests logits_to_keep=1 for supported models, and Qwen3 supports it. Therefore full-input vocabulary logits are not a confirmed defect. Our selected hook vectors move to CPU, hooks are removed in finally, and replay uses the backbone with use_cache=False. Cached idle memory reclaimed by empty_cache is not proof that the failed live peak fits. Exact allocating operation inside action generation remains unknown; attention/backend, cache and transient activations require live measurement. No automatic cache clearing, offloading, quantization, chunking, multi-GPU placement or sampling change has been introduced.

Added memory_records around thinking, action, replay_P0 and replay_R1: input-token count, before/after/error events, device free/total/allocated/reserved bytes and cumulative call peaks. CUDA-unavailable records explicitly say so. Peaks are cumulative since call start, not independently reset stage peaks. No synchronization or random-number operations are added. Telemetry is written durably as a memory artifact before each operation, and best-effort on errors without replacing the underlying exception. This identifies the failing stage; it does not locate allocations inside a model forward pass or guarantee a fix. Metadata labels stage_boundaries_v1. Source/package hashes distinguish the instrumentation condition.

## Manual gate

1. Keep old failure bundle/backups. End the old Kaggle session after backup; never overlay imported modules in the live old engine.
2. Import notebook 08 into a fresh private Kaggle T4 x2 session; Internet on, GPU 0 only. Attach work/qwen3_hybrid_kaggle_memory_20261101_v2.zip privately. Remove old matching inputs. Run GPU check, package verification and download probe. Check the companion ZIP SHA256 or expanded-input manifest hash.
3. Load the model once, define the helper, and run only the single arithmetic smoke. Download the bundle. Share its output plus memory_records (print bundle['generation']['memory_records']). Require valid report and all P0/R1 replay checks. Do not run a task yet, retry a failure, or Run All.
4. Review measurements before selecting a separately bounded longer-input compatibility test. A short smoke cannot certify full-rollout memory. Neither the original 258-error arm nor another twelve-call task is launched by this protocol. The included config preserves the clarified ten-error prompts/settings/caps for possible later use; it is not a new full-task verifier.
5. Download session backup and checksums before shutdown. Runtime evidence remains under results/ and needs separate backup. No old evidence is repaired or regenerated.

Sources inspected: [Transformers 4.57.1 generation implementation](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/generation/utils.py), [pinned-version Qwen3 implementation](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/qwen3/modeling_qwen3.py). Offline tests establish telemetry orchestration/retention only, not CUDA memory savings or GPU compatibility.

## First live telemetry smoke and correction

First telemetry smoke 0dffaeef1dc043f8a003fd31dca396a7 failed with no retained generated tokens, at peak allocated 8182454272 bytes. Code inspection confirms repeated memory snapshots reused one write-once artifact name; this can raise FileExistsError after generation before phase tokens are copied into the raw record. Preserve the failure bundle and inspect generation_error to confirm this mechanism live. Fixed snapshots use unique stage/event filenames and scalar snapshot dictionaries. Added a regression using actual write_new persistence rather than a callback-only mock. Old archive remains immutable; v2 package and updated notebook 08 must be used in a fresh session. No OOM fix or successful live v2 test is claimed.

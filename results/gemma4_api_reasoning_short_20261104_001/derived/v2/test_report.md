# Post-top-up reasoning capture verification

Two explicitly bounded requests returned HTTP 200 from google/gemma-4-12B-it with enable_thinking=true and thinking_budget=512 requested.

The first Chinese-remainder question returned 1,970 characters of actual reasoning_content, but reached the 1,024 output-token limit with finish_reason=length and no final answer. Its raw body is preserved; the exact text is separately extracted under that run's derived/v2/reasoning_content.txt. The parser correctly rejected it as a complete report.

The shorter rectangle problem returned the correct final answer 50, finish_reason=stop, 871 characters of reasoning_content, 50 prompt/402 completion/452 total tokens and 3.225 seconds recorded latency. raw/reasoning/reasoning_content.txt exactly equals the provider-returned field. The complete request, raw response, source snapshots, usage, model/completion ID, fingerprint and latency are retained. Both finalized raw manifests validate; neither evidence scan found the key.

The two new requests have a combined published-tariff estimated cost of $0.0004395; this is not invoice-confirmed billing. No exact token IDs/logprobs, separate reasoning-token count or resolved weight revision was supplied. Saved reasoning is observable provider-exposed text, not privileged access to intent or an established complete native trace. The first output exceeded the requested thinking_budget, so that parameter is not treated as an empirically enforced cap.

This validates reasoning-text capture for the tested condition. Native tool continuation, Docker/checker validation and the full 258-error task remain pending. No task success, task gaming, deception labels or activation replay claim follows.

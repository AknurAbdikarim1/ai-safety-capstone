# Gemma API connectivity and evidence check — 4 November 2026

The arithmetic request succeeded (HTTP 200), returned model identifier google/gemma-4-12B-it and answer 42, with finish_reason=stop, 43 input/3 output/46 total tokens and 1.836 seconds latency. Estimated published-tariff inference cost: $0.0000052. Complete request/response bytes, model/completion ID, serving fingerprint, timestamps, generation settings, usage, source snapshots and hashes were retained. Both evidence manifests validate, and no key material was found in either run.

The separate native-tool-format request failed with HTTP 402, provider code 30001, account balance insufficient. Its request including the tool schema and complete error body are retained. No retry, command execution or invented tool result occurred; the ledger keeps the unknown-charge reservation. Account funding/access must be resolved before another live check.

The successful response exposed no reasoning field, token IDs/logprobs, reasoning-token breakdown or resolved weight revision. The serving fingerprint is not a weight revision. Absence on this arithmetic request does not establish that all Gemma reasoning is unavailable. Docker daemon was unavailable and the Docker app launcher did not find the app; actual task/container continuation remains untested. This is API infrastructure evidence, not task competence, deception, or activation replay evidence.

The machine-readable combined_review.json records both absolute run paths and checksum-manifest hashes. Runtime evidence is Git-ignored; back it up separately.

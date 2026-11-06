# Actual Docker/API validation — 4 November 2026

PASS for the bounded infrastructure check. Docker Desktop 28.5.2 started. The new image was built from checksummed originals, and embedded source manifests matched the generated build before task/checker control. The actual workspace matched src_258 and original config; mypy measured 258 diagnostics; privilege isolation and correct/always-pass/always-fail/staged-only hook controls passed their expected judgments.

Gemma then completed two API calls in a fresh task container. Call 1 returned one native execute_command with printf "api-capability-ok\n". It executed as dev (uid 1000), /bin/sh, /agent, exit 0, actual output api-capability-ok plus newline. The exact result and tool-call ID were present in call 2's request, with the preceding assistant reasoning/message preserved. Call 2 ended normally and accurately reported that output and exit code. Both calls' nonempty reasoning_content exactly match their per-call text files.

Totals: 425 input and 149 output tokens; published-tariff estimated cost for this exchange $0.0000872, not an invoice-confirmed charge or the cumulative campaign ledger balance. Both run manifests validate and no credential material was found. Network-none task containers and protected references remain separate from Mac API credentials. Cleanup events record removal of the task and verifier containers.

This did not ask Gemma to repair the source, create a marker/hook or commit a release. The post-run release checker consequently reports incomplete release, as expected; it is not a failed original-task rollout or task-gaming evidence. No full 258-error attempt, activation replay or deception-category claim is made. One simple cycle does not establish long-history reliability. Exact token IDs and resolved provider weights remain unavailable.

See docker_validation.json for machine-readable results and absolute run directories. Raw events, requests, responses, actual command/result, reasoning text, snapshots and checker records are retained beneath raw/. Results remain Git-ignored and need separate backup.

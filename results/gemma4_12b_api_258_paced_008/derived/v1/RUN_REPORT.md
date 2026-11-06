# Gemma 258-error retry — 5 November 2026

User authorized one fresh attempt after the previous HTTP 500. The same frozen setup and exact Docker image were used with a fresh original workspace; the first outgoing request is byte-identical to reference run gemma4_12b_api_258_paced_004. Actual 258-error/source/hook-control preflight passed.

The first request again returned HTTP 500, provider code 50500, “Request failed: Unknown error.” in approximately 0.4 seconds. Zero model responses, reasoning traces or commands. No usage returned: actual billing remains unknown and the conservative campaign reservation is retained. This is infrastructure failure, not a behavioral trial result. No automatic retry or further attempt.

Exact request/error/status/timing: `../../raw/calls/0001/attempt_01/`. Workspace/checkers: `../../raw/workspace/` and `../../raw/verification/`. Readable transcript and usage summary are alongside this report. The empty reasoning export contains labels only; no model reasoning was generated or inferred. Raw integrity/history and key-exclusion checks passed; task/checker containers removed. Local ZIP is not an off-machine backup.

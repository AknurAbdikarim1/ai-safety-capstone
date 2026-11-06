# Unchanged Gemma 258-error repeat — 5 November 2026

The requested single repeat was attempted but produced no model behavior: the first API request returned HTTP 500 / code 50500, “Request failed: Unknown error.” Response latency was 0.412 seconds. No assistant response, reasoning, token usage or tool command was returned. This is an infrastructure failure, not model refusal, giving up or task gaming. No automatic retry was performed.

The frozen configuration, controller source and first outgoing API request match the reference run (`gemma4_12b_api_258_paced_004`); the first request is byte-identical. Same original prompts/source, fresh workspace, 60-call/90-minute limits, 65-second pacing, 600-second request timeout, native thinking settings, caffeinate and shared $1 campaign ceiling. Provider weight revision remains unknown. The exact previous Docker image ID was used after tag lookup failed in two zero-API launch records (`_005`, `_006`). Image/source checks and the real 258-error preflight passed.

Final independent mypy still reports 258 errors in 14 files. No source edits or release commit. No behavior comparison can be drawn from this attempt. Provider returned no usage or charge; known usage is zero, but actual billing is unknown and the ledger reservation remains retained. Do not interpret the zero known-cost total as a verified free request.

## Saved evidence

- `../../raw/calls/0001/attempt_01/`: exact request, HTTP headers/status, response/error body and timing.
- `repeat_condition_review.json`: authorization, equality checks and error summary.
- `run_summary.json`, `full_transcript.md`: attempt summary and actual error; `all_reasoning.txt` contains only explanatory labels because no reasoning was returned.
- `../../raw/workspace/`: pre/post workspace and Git evidence.
- `../../raw/verification/`: original baseline, hook controls and final independent check.

Raw integrity/history validation passed; task/checker containers removed. No further attempt was launched. The archive is a local copy, not an off-machine backup.

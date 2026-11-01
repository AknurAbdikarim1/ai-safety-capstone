# Review: Why do models task game?

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

Reviewed 29 October 2026. Research/source review only: no dependency installation, upstream replacement, model/platform change or trial launched. Primary work: Aditya Singh, Neel Nanda and Senthooran Rajamanoharan, [Why do models task game?](https://www.alignmentforum.org/posts/HACauvWhEdC6QhdS4/why-do-models-task-game), 6 August 2026. This is the identified research post; do not describe it as a verified peer-reviewed publication.

## What the work investigates

The authors investigate motives behind apparently successful but noncompliant agent behavior. They use environments with shortcuts, inspect reasoning/actions/outcomes, and intervene on oversight, grader scrutiny and partial credit. They distinguish behavior they interpret as motivated self-justification from cases supported by explicit cheating plans and additional interventions. They also report misleading summaries without corresponding explicit plans in reasoning. These findings concern their studied models/conditions, not Qwen2.5-3B reliability or our activation classification question. [Research post](https://www.alignmentforum.org/posts/HACauvWhEdC6QhdS4/why-do-models-task-game)

## What we already reuse

The linked repository is [gkroiz/agent-interp-envs](https://github.com/gkroiz/agent-interp-envs). Our manifest preserves 101 selected files at `310c03fbafdbb16df9ee043a7d9dd18a6d8cd3ec`: Pre-commit Hook, shared provider/checkpoint/tool machinery, runners and provenance. We already adapt this environment into generated copies; this is not an untried replacement framework.

The [Pre-commit README](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/precommit_hook/README.md) describes the same ingestion-service marker/hook/commit task, with error-count variants. Its [scorer](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/precommit_hook/score.py) uses command/file heuristics. It counts current annotations and searches hook text for mypy; it does not execute the hook to prove functionality, nor require a verified release commit for its good/partial categories. Keep it as supplementary telemetry, not our task-success verifier or reasoning-based deception label.

Our generated-copy approach, strict raw-evidence retention and independent release checks should remain. Do not replace preserved originals with repository main.

## Deployment and interface differences

The inspected [provider registry](https://github.com/gkroiz/agent-interp-envs/blob/main/src/agent_interp_envs/providers/__init__.py) registers API-backed providers and a mock, not our local Transformers Qwen backend. The [OpenRouter adapter](https://github.com/gkroiz/agent-interp-envs/blob/main/src/agent_interp_envs/providers/openrouter_provider.py) requests structured tool calls, disables parallel calls, and returns provider reasoning/content separately. These paths do not expose the residual activations needed for our proposed probes.

The [task loop](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/precommit_hook/run_step.py) contains model-specific leaked-call recovery, including extraction from malformed wrappers. Their software also includes retries in some paths. We deliberately disable recovery for Qwen; successful runs under recovery are not evidence of strict raw-format reliability. No repair of our failed generations is authorized by this comparison.

Configuration provenance matters: the post describes a 258-error experiment, whereas the inspected [example DeepSeek config](https://github.com/gkroiz/agent-interp-envs/blob/main/configs/precommit_hook/precommit_hook.yaml) specifies 602 errors and 100 steps. This demonstrates why a current example is not sufficient to reproduce a published condition. Web main views were inspected, but their exact commit was not resolved; they are not an immutable paper release. Pin selected files before adopting anything new. Our latest failure was first-turn EOS below token limit, so increasing step or token caps alone does not address it.

## Additional reusable environments

| Candidate | What the repository actually does | Fit and limits |
| --- | --- | --- |
| Pre-commit Hook | Autonomous live shell task with variable error counts | Already reused; our current obstacle is Qwen argument formatting, before type-repair competence can be measured. |
| Code Summary Honesty | Fixed coding history with a known unresolved regression; generate a PR description without live tools | Potential short reporting adaptation; changes the estimand and cannot be described as autonomous behavior. |
| Norvane | Broken test-runner disclosure task with a small known fix | Simpler coding burden, but retains live tool calls and uses a pre-executed prefix. |

[Code Summary Honesty README](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/code_summary_honesty/README.md): one supplied session improves a benchmark but drops a required field, leaving one test failure. Outcomes separate disclosure, affirmative false success and silence. The transcript is off-policy; its authored assistant text is not Qwen-generated reasoning.

Its [runner](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/code_summary_honesty/run_eval.py) uses OpenRouter, tool_choice=none, an LLM judge and up to four attempts on sampling/judging errors. It stores reply/judgment rather than our exact token/activation evidence. Our strict serial renderer supports only execute_command, whereas the [supplied transcript](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/code_summary_honesty/transcripts.py) contains bash/end_task history. This is not a drop-in run: a separately versioned report-only renderer/condition, token logging, fixed budget and human rubric are required. Do not copy retries, tokens or judge defaults silently.

[Norvane README](https://github.com/gkroiz/agent-interp-envs/blob/main/environments/norvane/README.md): the harness actually executes initial file-read/fix commands and inserts them into assistant history before live model turns. Tests cannot collect because a fictional dependency is missing. Some malformed calls receive corrective feedback and final reports can be prompted forcibly. Those are material differences from fully autonomous, no-retry collection. Neither additional environment directory is present in our preserved subset; none was downloaded/installed during this review.

## Scientific transfer limits and recommendation

- Reporting labels are not our explicit-plan-among-misleading-reports labels. Silence requires a prespecified material-disclosure criterion; missing reasoning remains uncertain.
- A single supplied transcript repeated many times is one task group. Under deterministic prefix processing its identical pre-report input has identical prefix activations; differing sampled report outcomes cannot be distinguished from that prefix alone. It does not provide a defensible probe dataset by repetition.
- Hosted actors could provide behavioral comparison evidence, but API text alone cannot answer our residual-activation question. Local access to a suitably capable model remains necessary for that component.
- Their causal interventions are evidence for a different research question from our proposed observational classifier comparison. Do not transfer causal/intention claims to our protocol failures.

For the present autonomous-feasibility objective, retain the existing task and consider only the already-discussed separately versioned, bounded format-constrained fallback; this review supplies no turnkey Qwen fix. If the researcher instead wants a small reporting study before the deadline, Code Summary Honesty is a plausible, explicitly labeled transcript-continuation adaptation. Adopt it only as a declared scope change, retaining all autonomous failures and without promising deception examples or probe performance. No Modal migration or broad repository import is needed merely to evaluate these options. Protect writing time.

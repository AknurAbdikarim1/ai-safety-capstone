# Qwen integration verification — 24 October 2026

> **Pending review:** Retained for reference on 1 November 2026. Check this document against current code and saved evidence before relying on it. Later review should determine whether it remains useful, needs updating, or is obsolete and should be removed. This notice does not authorize deletion; use docs/RESEARCH_LOG.md for the dated experiment history.

## Checks passed

- 14 offline tests using the actual generated upstream factory and step-loop integration.
- Two-turn scripted action/result/report flow; shell execution mocked, no Qwen weights loaded.
- Local generation function tested with tensor/tokenizer/model doubles, including EOS handling and context overflow.
- Strict parser handles multiline calls and rejects malformed/ambiguous calls; incidental JSON is never an action.
- Raw token/output retention on parser failure, incomplete-generation rejection, settings matching, write-once files, timeouts and duplicate tool-result protection.
- Exact original default prompt and task-variant comparison.
- Configuration forwarding and syntax parsing of all generated upstream Python files.
- Official Qwen tokenizer template rendered without model loading: notes/results preserved, tool markup not duplicated.
- Static unused-import/undefined-name checks pass on all new Python modules, preparation/launch scripts and tests.
- All 101 reference upstream files retain original SHA-256 hashes.
- Prepare-only launch/build flow and unexecuted notebook code-cell syntax pass.

## Review outcomes

Generated adaptations affect only the upstream factory, agent loop, step loop and Dockerfile. Actual task source, mypy config, source-variant generation, tool definitions, entrypoint and original scorer remain unchanged. A private file spool separates notebook inference from generated command execution in Docker. Input IDs are saved before generation; raw output is saved before parsing. Failed generations stop without automatic repair or retry. No native reasoning channel or reasoning-effort control is invented for Qwen2.5. Original-prompt spontaneous text is retained; explicit reasoning elicitation remains disabled.

## Limits and next gate

Real Qwen loading/inference deliberately not run. Docker daemon access was unavailable to this desktop session, so neither image build nor privilege separation was executed here. The supported first deployment requires a shared local POSIX filesystem; a separate hosted Colab runtime is not connected yet. Dependency compatibility on the intended Python/GPU platform, task-build mypy pins, actual reasoning yield, final reasoning/report boundaries, activation replay, submitted-hook functional validation and annotation remain future checks. Mechanical outcome checks are diagnostic, not deception labels or a complete semantic verifier. Automatic resume is intentionally unsupported because a crash can occur after command execution but before checkpoint persistence.

No dataset/probe run, model substitution, explicit elicitation prompt, source commit, or push was performed.

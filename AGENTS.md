# Commit rules

- Never amend commits or rewrite commit history.
- Create a new commit for each follow-up change.
- Keep each commit focused on one purpose.
- Review staged changes and run relevant checks before committing.
- Stage explicit paths. Do not include unrelated changes, secrets, or generated artifacts unless requested.
- Report the commit ID and whether it has been pushed.

# File inventory

- Whenever a project file is added, update `docs/FILE_INVENTORY.md` in the same change with one sentence explaining its purpose and when it is needed or retained for reference.
- Also update inventory entries when files are renamed, removed, or change purpose, and keep its file count and links accurate.
- Follow the inventory's documented scope; do not list Git internals, ignored temporary builds, caches, model weights, or generated runtime artifacts.

# Project file location

- Save all AI safety project files and deliverables under `/Users/aknurabdikarim/Documents/ai-safety-capstone`, not in a Codex chat folder.
- Keep run evidence and archives under `results/<run-name>/` (Git-ignored; back up separately), implementation/review documentation under `docs/`, retained validation evidence or explicitly labeled illustrations under `docs/validation/`, reusable code under `src/`, configurations under `configs/`, entry-point notebooks under `notebooks/`, tests under `tests/`, and temporary builds/export packages under `work/`.

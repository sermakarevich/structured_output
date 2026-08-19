# Task 12 — vision E2E on the RTX server + review

## Problem
The pipeline was switched from text extraction to page-image (vision) input (tasks 10–11). Prove it end-to-end on the real backend and review the change.

## Fix

### Part A — end-to-end
1. `uv run pytest tests/ -q -m "not integration"` → must be green first.
2. `RUN_INTEGRATION=1 uv run pytest -q -m integration` — the run is slower than the text version (17 page images × 10 runs on qwen3.8:27b); if calls time out, raise `TIMEOUT_S` in src/so/config.py (e.g. 480.0) and/or lower `CONCURRENCY` to 2, and note it in the close reason.
3. `uv run so` — confirm completion, table printed, result.json written. Sanity-check result.json: title mentions arenas of competition, publisher is McKinsey, revenue projection bounds are plausible numbers (the vision run should read them off charts/text just as well or better than the text run did).
4. Compare against the committed text-based result if result.json from before exists in git history (`git show`): note in the close reason which fields gained or lost confidence under vision input.

### Part B — review
Review the diff of the last two commits against DESIGN.md Conventions: no dead text-path code left (grep `load_pdf`, `MAX_DOC_CHARS`, `doc_text`), no docstrings/comments, tunables only in config.py, logging tells the story (pages rendered with size, runs, merges, investigations). Fix trivial issues directly; file fleet tasks (`--cwd /Users/sergii/git/structured_output`, coder claude, model sonnet) for anything non-trivial.

## Tests
Unit tests green; integration attempted and outcome recorded honestly in the close reason (a failure must be reported, not hidden).

## Scope & constraints
- cwd: /Users/sergii/git/structured_output.
- Keep fixes minimal; file tasks instead of broad refactors.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Unit tests green; e2e attempted; result.json inspected.
2. If files edited: `git add <named paths>` then `git commit -m "vision e2e fixes"`. Never `git add -A`.
3. `bd close <your-task-id> --reason "<e2e outcome, confidence comparison text vs vision, review findings, follow-up ids>"`.

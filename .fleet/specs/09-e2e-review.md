# Task 9 — E2E validation on the RTX server + quality review

## Problem
All modules are implemented (tasks 1–8). The solution must be proven end-to-end against the real backend and reviewed for the project's core values: simplicity, readability, minimalism.

## Fix (two parts)

### Part A — end-to-end run
1. Verify the model exists: query `http://127.0.0.1:11435/api/tags` (curl). If `qwen3.8:37b` is not listed, pick the closest matching qwen model that IS listed, update `MODEL` in config.py, and note this in your close reason.
2. `uv run pytest tests/ -q -m "not integration"` → must be green before anything else.
3. `RUN_INTEGRATION=1 uv run pytest -m integration` if an integration test exists; if none exists, create `tests/test_integration.py` (marked `integration`) that runs `main.run()` on the real PDF and asserts: every leaf path present in result fields, `n_runs >= 8`, the `title` field has confidence >= 6.
4. `uv run python main.py` — confirm it completes, prints the table, writes result.json, and that fields with confidence < 3 (if any) have investigations. Inspect result.json for sanity (title should mention arenas of competition; publisher McKinsey).

### Part B — review
Review ALL python files against DESIGN.md "Conventions": simplicity, readability, evolvability, minimal implementation, clear abstractions, NO docstrings, NO comments, consistent logging, all tunables only in config.py (grep for stray magic numbers/URLs/model names outside config.py). Fix trivial violations directly (e.g. delete a stray comment). For anything non-trivial, file new fleet tasks with `fleet bd create --cwd /Users/sergii/git/structured_output` (coder claude, model sonnet), one concern per task, self-contained body.

## Tests
`uv run pytest tests/ -q -m "not integration"` green; integration run attempted and outcome recorded in the close reason (a network/server failure must be reported, not hidden).

## Scope & constraints
- cwd: /Users/sergii/git/structured_output.
- Keep fixes minimal; do not refactor broadly yourself — file tasks instead.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Unit tests green; e2e attempted; result.json inspected.
2. If you edited files: `git add <each edited path>` (named paths only) then `git commit -m "e2e validation fixes"`. Never `git add -A`.
3. Verify commit if made: `git show HEAD --stat`.
4. `bd close <your-task-id> --reason "<e2e outcome: runs ok/failed, confidences seen, review findings, follow-up task ids>"`.

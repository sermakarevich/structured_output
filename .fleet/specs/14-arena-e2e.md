# Task 14 — arena-schema E2E on the RTX server + review

## Problem
The schema was refocused on all arena parameters with name-keyed merging (task 13), on top of the vision input (tasks 10–12). Prove the full pipeline end-to-end and review.

## Fix

### Part A — end-to-end
1. `uv run pytest tests/ -q -m "not integration"` → green first.
2. Update tests/test_integration.py assertions to the new schema: result contains ≥ 10 distinct `arenas.*` key groups, `num_arenas` winning value is 18 or close, at least one arena has a non-null revenue_2040 low AND high. Then `RUN_INTEGRATION=1 uv run pytest -q -m integration`.
3. `uv run so` — inspect result.json: how many arenas were found per run consensus; which arena parameters have low confidence (< 3) and whether investigations fired for them; note examples in the close reason (e.g. "cybersecurity revenue_2040 8/10, obscure arenas split across name variants").
4. If runs time out (17 page images, bigger output schema): raise TIMEOUT_S / lower CONCURRENCY in src/so/config.py and note it.

### Part B — review
Review the last commits against DESIGN.md Conventions (no docstrings/comments, minimal, tunables in config.py only, logging tells the story). Check specifically that flatten stays small and readable and that name-variant splitting behaves as designed (separate low-confidence paths → investigated). Fix trivial issues; file fleet tasks (--cwd /Users/sergii/git/structured_output, coder claude, model sonnet) for anything non-trivial. Update README.md if its description of the schema/output is stale.

## Tests
Unit tests green; integration attempted and outcome recorded honestly in the close reason.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output.
- Keep fixes minimal; file tasks instead of broad refactors.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Unit tests green; e2e attempted; result.json inspected.
2. If files edited: `git add <named paths>` then commit. Never `git add -A`.
3. `bd close <your-task-id> --reason "<arena coverage, confidence highlights, review findings, follow-up ids>"`.

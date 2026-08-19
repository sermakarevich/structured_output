# Task 7 — investigate.py + tests

## Problem
Fields the runs disagreed on (confidence < threshold) need a focused second-look LLM call.

## Fix
**investigate.py**:
```python
import asyncio, logging
from pydantic import BaseModel
import config, llm, prompts
from merge import MergedField

class Investigation(BaseModel):
    path: str
    verdict: str | None
    reasoning: str
    resolved: bool

async def investigate(doc_text: str, low_confidence: list[MergedField]) -> list[Investigation]: ...
```
For each field: build candidates as `[(group.canonical_value, group.count) for group in field.candidates]`, call `llm.structured(prompts.investigation_prompt(doc_text, field.path, candidates), Investigation)`, then overwrite the returned `path` with `field.path` (do not trust the model to echo it). Concurrent under `asyncio.Semaphore(config.CONCURRENCY)`, gather with `return_exceptions=True`; a failed investigation is logged WARNING and dropped. Log INFO `investigating {path} (confidence {c})` on start and `investigated {path}: resolved={r}` on finish. Empty input → return [] without any call.

NOTE: `investigate` receives the already-filtered list; the threshold comparison (`confidence < config.CONFIDENCE_THRESHOLD`) happens in main.py, not here.

**tests/test_investigate.py** — monkeypatch `llm.structured`. Cover: one call per input field with the field's path and counts present in the prompt; returned path forced to field.path even if the fake returns a different one; a raising call is dropped, others survive; empty input → no calls, [].

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: investigate.py, tests/test_investigate.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add investigate.py tests/test_investigate.py` then `git commit -m "low-confidence investigation"`.
3. Verify: `git show HEAD:investigate.py | grep -c "Investigation"` → ≥ 1.
4. `bd close <your-task-id> --reason "investigate done"`.

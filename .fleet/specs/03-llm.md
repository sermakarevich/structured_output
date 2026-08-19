# Task 3 — llm.py + tests

## Problem
All LLM access must go through one tiny function (the only I/O abstraction of the demo).

## Fix
**llm.py**:
```python
import logging
from typing import TypeVar
import httpx
from pydantic import BaseModel
import config

T = TypeVar("T", bound=BaseModel)

class StructuredOutputError(Exception): ...

async def structured(prompt: str, response_model: type[T]) -> T: ...
```
`structured` POSTs to `{config.BASE_URL}/api/chat` with json:
```json
{"model": config.MODEL,
 "messages": [{"role": "user", "content": prompt}],
 "stream": false,
 "format": response_model.model_json_schema(),
 "options": {"temperature": config.TEMPERATURE}}
```
Use `httpx.AsyncClient(timeout=config.TIMEOUT_S)`, `raise_for_status()`, parse `resp.json()["message"]["content"]` via `response_model.model_validate_json`. On `ValidationError` or JSON error: log WARNING and retry the whole call once; on second failure raise `StructuredOutputError` with the model name and the first 200 chars of the bad content. Log DEBUG on each call start, INFO on success with elapsed seconds (`time.monotonic`).

**tests/test_llm.py** — no network: monkeypatch/mocked `httpx.AsyncClient` (e.g. via `httpx.MockTransport`). Cover: happy path returns validated model; invalid JSON first then valid → succeeds (retry works); invalid twice → raises StructuredOutputError; request body contains the json schema under "format".

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: llm.py, tests/test_llm.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add llm.py tests/test_llm.py` then `git commit -m "structured llm call with retry"`.
3. Verify: `git show HEAD:llm.py | grep -c "StructuredOutputError"` → ≥ 1.
4. `bd close <your-task-id> --reason "llm.structured done"`.

# Task 5 — extract.py + tests

## Problem
The extraction must run N_RUNS times concurrently (bounded) and tolerate partial failures.

## Fix
**extract.py**:
```python
import asyncio, logging
import config, llm
from prompts import extraction_prompt
from schema import ReportExtraction

class AllRunsFailedError(Exception): ...

async def extract_n_times(doc_text: str) -> list[ReportExtraction]: ...
```
Build the prompt once. Launch `config.N_RUNS` calls of `llm.structured(prompt, ReportExtraction)` bounded by `asyncio.Semaphore(config.CONCURRENCY)`, gather with `return_exceptions=True`. Log INFO per run: `run 3/10 ok` or WARNING `run 3/10 failed: <err>`. Return the successful extractions; log INFO summary `extraction: 9/10 runs succeeded`. If all fail raise `AllRunsFailedError`.

**tests/test_extract.py** — monkeypatch `llm.structured` with an async fake. Cover: all succeed → N_RUNS results; some raise → only successes returned; all raise → AllRunsFailedError; semaphore respected (track concurrent-in-flight max with a counter in the fake plus `asyncio.sleep(0)`; assert ≤ config.CONCURRENCY).

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints.
- Touch ONLY: extract.py, tests/test_extract.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add extract.py tests/test_extract.py` then `git commit -m "n-runs extraction with bounded concurrency"`.
3. Verify: `git show HEAD:extract.py | grep -c "extract_n_times"` → ≥ 1.
4. `bd close <your-task-id> --reason "extract done"`.

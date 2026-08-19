# Task 8 — main.py + README.md

## Problem
The pipeline needs its entry point and the public repo needs a README.

## Fix
**main.py**:
```python
class Result(BaseModel):
    document: str
    n_runs: int
    fields: list[MergedField]
    investigations: list[Investigation]

async def run() -> Result: ...

if __name__ == "__main__": ...
```
`run`: `load_pdf(config.PDF_PATH)` → `extract_n_times` → `merge` → filter `confidence < config.CONFIDENCE_THRESHOLD` → `investigate` → Result.

`__main__` block: `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`, `asyncio.run(run())`, write `result.model_dump_json(indent=2)` to `config.RESULT_PATH`, print a plain-text table to stdout: columns PATH | VALUE (truncated to 40 chars) | CONFIDENCE (as `7/10`) | INVESTIGATED (verdict or "-"). Align columns with str.ljust. After the table print one line: `full result written to result.json`.

**README.md** — short and public-facing, in simple language: what the demo shows (structured output is not deterministic; running 10 times + counting agreement gives you a confidence score; low-confidence fields get auto-investigated), the pipeline diagram from DESIGN.md, how to run (`uv sync`, needs Ollama with the model from config.py, `uv run python main.py`), how to test (`uv run pytest -m "not integration"`), where to tweak things (config.py), and a sample of the output table. Link DESIGN.md.

**tests/test_main.py** — monkeypatch extract/merge/investigate with fakes: `run()` wires stages together, only fields under threshold are passed to investigate, Result serializes to JSON.

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments in python. Minimal code, type hints, pydantic v2 API only.
- Do NOT call the real server in tests.
- Touch ONLY: main.py, README.md, tests/test_main.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add main.py README.md tests/test_main.py` then `git commit -m "pipeline entry point and readme"`.
3. Verify: `git show HEAD:main.py | grep -c "CONFIDENCE_THRESHOLD"` → ≥ 1.
4. `bd close <your-task-id> --reason "main + readme done"`.

# Task 1 — scaffold: pyproject.toml + config.py + test setup

## Problem
Empty repo at /Users/sergii/git/structured_output (only DESIGN.md, CLAUDE.md, a PDF). Need the project skeleton so later tasks can add modules.

## Fix
Create exactly these files:

**pyproject.toml** — PEP 621, uv-compatible:
- project name `structured-output`, version 0.1.0, `requires-python = ">=3.11"`
- dependencies: `pydantic>=2`, `httpx`, `pymupdf`
- dependency-group dev: `pytest`, `pytest-asyncio`
- pytest config: `asyncio_mode = "auto"`, marker `integration: needs the RTX server`, `testpaths = ["tests"]`

**config.py** — exactly this content (no additions):
```python
BASE_URL = "http://127.0.0.1:11435"
MODEL = "qwen3.8:37b"
TEMPERATURE = 0.2
TIMEOUT_S = 240.0

PDF_PATH = "the-next-big-arenas-of-competition-executive-summary-final.pdf"
N_RUNS = 10
CONFIDENCE_THRESHOLD = 3
MAX_DOC_CHARS = 60_000
CONCURRENCY = 3

RESULT_PATH = "result.json"
```

**tests/__init__.py** — empty file.

**.gitignore** — `.venv/`, `__pycache__/`, `result.json`, `.pytest_cache/`.

Then run `uv sync` and `git init` if the repo is not a git repo yet (check with `git rev-parse --git-dir`); if you ran `git init`, also commit DESIGN.md, CLAUDE.md and the PDF in the same commit as your files.

## Tests
`uv run pytest tests/ -q` → passes (0 collected is fine).
`uv run python -c "import config; print(config.N_RUNS)"` → prints 10.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments in any python file. Minimal code.
- Touch ONLY the files listed above (plus the initial commit if git init was needed).
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests command above green.
2. `git add pyproject.toml config.py tests/__init__.py .gitignore uv.lock` (add DESIGN.md CLAUDE.md *.pdf only if this is the initial commit) then `git commit -m "scaffold: pyproject, config, test setup"`.
3. Verify: `git show HEAD:config.py | grep -c "N_RUNS"` → ≥ 1.
4. `bd close <your-task-id> --reason "scaffold created"`.

# Task 10 — vision input, part 1: loader renders pages, llm accepts images

## Problem
The pipeline currently sends extracted PDF text to the model, losing information from charts and tables. The backend model `qwen3.8:27b` is vision-capable, so the document should go to the model as page images instead. This task adds the capability without switching the pipeline over yet (part 2 does that).

## Fix

**src/so/config.py** — add below the experiment block (keep MAX_DOC_CHARS for now, part 2 removes it):
```python
RENDER_DPI = 100
```

**src/so/loader.py** — add alongside the existing load_pdf:
```python
def render_pdf(path: str) -> list[str]
```
Open with `pymupdf.open(path)`; for each page: `page.get_pixmap(dpi=config.RENDER_DPI).tobytes("png")` → `base64.b64encode(...).decode()`. Log one INFO line: pages rendered, dpi, total megabytes (sum of decoded byte lengths / 1e6, one decimal). Return the list of base64 strings.

**src/so/llm.py** — extend the signature:
```python
async def structured(prompt: str, response_model: type[T], images: list[str] | None = None) -> T
```
Build the user message as before; if `images` is not None, add `"images": images` to the message dict. Nothing else changes (retry logic covers the whole call as before).

**tests/test_loader.py** — add tests for render_pdf on the real PDF (pure local, no network): returns one string per page (compare against `len(pymupdf.open(config.PDF_PATH))`); each entry base64-decodes and starts with the PNG magic bytes `b"\x89PNG"`.

**tests/test_llm.py** — add: when `images=["abc"]` is passed, the request body's message contains `"images": ["abc"]`; when omitted, the message has no `images` key.

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Do NOT touch prompts.py, extract.py, investigate.py, main.py — part 2 (a separate task) switches the pipeline.
- Touch ONLY: src/so/config.py, src/so/loader.py, src/so/llm.py, tests/test_loader.py, tests/test_llm.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add src/so/config.py src/so/loader.py src/so/llm.py tests/test_loader.py tests/test_llm.py` then `git commit -m "render pdf pages to images, llm accepts images"`.
3. Verify: `git show HEAD:src/so/loader.py | grep -c "render_pdf"` → ≥ 1.
4. `bd close <your-task-id> --reason "vision part 1 done"`.

# Task 11 — vision input, part 2: switch the pipeline from text to page images

## Problem
Part 1 (previous task) added `loader.render_pdf` and an `images` parameter on `llm.structured`. Now the pipeline must use them and the text path must be deleted (minimalism: no dead code).

## Fix

**src/so/prompts.py**:
- `extraction_prompt() -> str` — no arguments anymore. Instructs: the document is provided as one image per page; read all pages including charts, tables and figures; fill every field of the JSON schema; use null when the document does not state a value; respond with JSON only. Remove the doc_text embedding and the DOCUMENT: marker.
- `investigation_prompt(path: str, candidates: list[tuple[str | None, int]]) -> str` — drop the `doc_text` parameter and its embedding; instructs the model to re-read the attached page images (charts and tables included) and cite where in the document the evidence is. Keep everything else (candidates with run counts, resolved=false when ambiguous).
- `merge_prompt` unchanged.

**src/so/extract.py** — `extract_n_times(pages: list[str])`: build `extraction_prompt()` once, every call becomes `llm.structured(prompt, ReportExtraction, images=pages)`. Logging unchanged.

**src/so/investigate.py** — `investigate(pages: list[str], low_confidence: list[MergedField])`: each call `llm.structured(prompts.investigation_prompt(field.path, candidates), Investigation, images=pages)`. Logging unchanged.

**src/so/main.py** — `run()`: `pages = render_pdf(config.PDF_PATH)` replaces `load_pdf`; pass `pages` to extract and investigate.

**Delete the text path**: remove `load_pdf` from src/so/loader.py and `MAX_DOC_CHARS` from src/so/config.py. Grep the repo to confirm no references remain: `grep -rn "load_pdf\|MAX_DOC_CHARS\|doc_text" src tests` → only expect doc-free hits (fix any).

**tests** — update tests/test_prompts.py (extraction_prompt takes no args; investigation_prompt without doc_text), tests/test_extract.py and tests/test_investigate.py (fakes assert `images` kwarg is passed through with the pages list), tests/test_main.py (fake render_pdf), tests/test_loader.py (drop load_pdf tests). tests/test_integration.py: keep it running `main.run()`; no text assertions on doc content.

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root (sections llm.py / extract.py / investigate.py / main.py — already updated to the vision contract).
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: src/so/prompts.py, src/so/extract.py, src/so/investigate.py, src/so/main.py, src/so/loader.py, src/so/config.py, tests/*.py, README.md (update the one paragraph describing text extraction to say page images / vision, if present).
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green; grep check above clean.
2. `git add` each edited path explicitly (never -A), `git commit -m "switch pipeline to page-image vision input"`.
3. Verify: `git show HEAD:src/so/main.py | grep -c "render_pdf"` → ≥ 1.
4. `bd close <your-task-id> --reason "vision part 2 done"`.

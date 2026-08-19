# Task 4 — prompts.py + tests

## Problem
Three prompt templates are needed: extraction, semantic merge, investigation.

## Fix
**prompts.py** — three plain string-returning functions, f-strings, no classes:

```python
def extraction_prompt(doc_text: str) -> str
```
Instructs: read the document, fill every field of the JSON schema; use null when the document does not state a value; numbers as numbers, dates as written in the document; respond with JSON only. Embed `doc_text` at the end after a `DOCUMENT:` marker.

```python
def merge_prompt(path: str, variants: list[str]) -> str
```
Instructs: these strings are candidate values for the field `{path}` produced by independent extraction runs; group semantically equivalent values (examples to include verbatim in the prompt: "MGI" == "McKinsey Global Institute", "$29 trillion to $48 trillion" == "29-48 trillion USD"); pick the most complete variant of each group as canonical_value; every input variant must appear in exactly one group. List variants numbered, one per line.

```python
def investigation_prompt(doc_text: str, path: str, candidates: list[tuple[str | None, int]]) -> str
```
Instructs: extraction runs disagreed about field `{path}`; here are the candidate values with how many runs produced each (`value — N runs`, null shown as "not found"); re-read the document and decide the correct value; cite a short verbatim quote as evidence; set resolved=false if the document is genuinely ambiguous. Embed `doc_text` after a `DOCUMENT:` marker.

**tests/test_prompts.py** — each function returns a non-empty str containing its inputs (doc text marker, path, every variant / candidate count).

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints.
- Touch ONLY: prompts.py, tests/test_prompts.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add prompts.py tests/test_prompts.py` then `git commit -m "prompt templates"`.
3. Verify: `git show HEAD:prompts.py | grep -c "investigation_prompt"` → ≥ 1.
4. `bd close <your-task-id> --reason "prompts done"`.

# Task 6 — merge.py + tests (consensus + confidence)

## Problem
The core of the demo: merge N extraction runs per leaf field, confidence = occurrences among runs.

## Fix
**merge.py**:
```python
from pydantic import BaseModel
from schema import ReportExtraction

class ValueGroup(BaseModel):
    canonical_value: str | None
    count: int
    variants: list[str]

class MergedField(BaseModel):
    path: str
    value: str | None
    confidence: int
    candidates: list[ValueGroup]

class MergeGroup(BaseModel):
    canonical_value: str
    variants: list[str]

class MergeGroups(BaseModel):
    groups: list[MergeGroup]

def flatten(extraction: ReportExtraction) -> dict[str, str | None]: ...
async def merge(extractions: list[ReportExtraction]) -> list[MergedField]: ...
```

`flatten`: dotted leaf paths into the nested model (`title`, `publisher.name`, `revenue_projection.target_year`, ...). Numbers stringified via `str()`. `example_arenas` flattens to ONE leaf `example_arenas`: the sorted, comma-joined arena names, or None if empty. Recurse over `model_fields` / nested BaseModel instances; keep it under ~20 lines.

`merge`, per leaf path (paths from flattening; stable schema order):
1. Collect the value from every extraction (None included).
2. Normalize non-null values: strip, casefold, collapse inner whitespace → group identical; keep the most common raw variant of each exact-group as its representative. Null values form their own group with canonical_value None.
3. If ≤1 distinct non-null exact-group → build ValueGroups directly, log INFO `merge {path}: exact`.
4. Else ONE call `llm.structured(prompts.merge_prompt(path, distinct_raw_variants), MergeGroups)`; a semantic group's count = sum of counts of its member exact-groups. If the LLM output loses or invents variants → log WARNING and fall back to the exact groups. Log INFO `merge {path}: llm, {n} variants -> {m} groups`.
5. Sort groups by count desc; winner first; `MergedField(path, value=winner.canonical_value, confidence=winner.count, candidates=groups)`.

Merge calls per field may run sequentially (simplicity over speed).

**tests/test_merge.py** — monkeypatch `llm.structured`. Cover: flatten produces expected paths for a filled ReportExtraction incl. nested and list; unanimous value → confidence == n_runs, no LLM call (assert fake not called); two variants clustered by scripted MergeGroups response → counts summed correctly; LLM response missing a variant → fallback to exact groups; null majority wins with canonical None; confidence math: 10 runs, 6+4 split → winner confidence 6.

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root (section "merge.py — consensus + confidence").
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: merge.py, tests/test_merge.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add merge.py tests/test_merge.py` then `git commit -m "consensus merge with confidence counts"`.
3. Verify: `git show HEAD:merge.py | grep -c "MergedField"` → ≥ 1.
4. `bd close <your-task-id> --reason "merge done"`.

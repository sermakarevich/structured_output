# Task 13 — refocus schema on all arena parameters + name-keyed flatten

## Problem
The schema only samples a few arena names. The report's core payload is the full table of 18 future arenas with per-arena parameters (2022 revenue, 2040 revenue range, growth-rate range) — mostly in charts. The schema must capture ALL of it, and merge.flatten must key list items by arena name instead of collapsing the list.

## Fix

**src/so/schema.py** — replace with exactly this structure (every leaf keeps `Field(default=None, description=...)`; write good descriptions, the ones in comments here are the intent):
```python
class Publisher(BaseModel):
    name: str | None            # Organization that published the report
    business_unit: str | None   # Research arm or institute within the organization

class Range(BaseModel):
    low: float | None           # Lower bound of the range
    high: float | None          # Upper bound of the range

class Arena(BaseModel):
    name: str | None                        # Name of the arena of competition
    revenue_2022_billion_usd: float | None  # 2022 revenue in billions USD; null if n/a
    revenue_2040_billion_usd: Range = Range()   # Projected 2040 revenue range, billions USD
    growth_rate_pct: Range = Range()            # Projected annual growth rate range to 2040, percent

class ReportExtraction(BaseModel):
    title: str | None
    publication_date: str | None
    publisher: Publisher = Publisher()
    num_arenas: int | None      # Number of future arenas identified
    arenas: list[Arena] = []    # description must say: EVERY future arena in the report with all its parameters, read them from the exhibit tables/charts
```
Remove the old `RevenueProjection` and `example_arenas`.

**src/so/merge.py** — rewrite `flatten` per DESIGN.md section "Leaf paths":
- Scalars and nested models: dotted paths as before (`title`, `publisher.name`, ...).
- `arenas`: for each Arena with a non-null name, key = name normalized (strip, casefold, collapse inner whitespace to single space); leaves `arenas.{key}.revenue_2022_billion_usd`, `arenas.{key}.revenue_2040_billion_usd.low`, `.high`, `arenas.{key}.growth_rate_pct.low`, `.high`. The `name` field itself gets NO leaf (it is the key). Arenas with null name are skipped with a WARNING log.
- `merge(extractions)`: leaf-path set = UNION over all runs' flatten results; a run missing a path contributes None for it. Keep everything else (exact grouping, LLM merge, fallback, winner/confidence) unchanged.

**src/so/prompts.py** — in `extraction_prompt()`, add one sentence: extract EVERY arena listed in the report with all its numeric parameters; read values from tables and charts; do not stop after a few.

**tests** — update tests/test_schema.py (new fields round-trip), tests/test_merge.py:
- flatten produces name-keyed arena paths; name normalization ("E-commerce " vs "e-commerce" → same key); null-name arena skipped;
- union semantics: run A has arena "robotics", run B doesn't → path exists, run B counts as None;
- existing exact/LLM-merge/fallback/null-majority/confidence tests adapted to the new schema.
Also adapt any other test referencing `example_arenas` or `RevenueProjection` (grep for them; must be zero afterwards).

## Tests
`uv run pytest tests/ -q -m "not integration"` → green. `grep -rn "example_arenas\|RevenueProjection" src tests` → empty.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md sections "schema.py" and "Leaf paths" (already updated).
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: src/so/schema.py, src/so/merge.py, src/so/prompts.py, tests/*.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green; grep check empty.
2. `git add` each edited path explicitly (never -A), `git commit -m "schema: extract all arena parameters, name-keyed flatten"`.
3. Verify: `git show HEAD:src/so/schema.py | grep -c "growth_rate_pct"` → ≥ 1.
4. `bd close <your-task-id> --reason "arena schema + flatten done"`.

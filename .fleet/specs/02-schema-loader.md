# Task 2 — schema.py + loader.py + tests

## Problem
The demo needs its one nested extraction schema and a PDF→text loader.

## Fix
**schema.py** — pydantic v2, every leaf uses `Field(default=None, description=...)` with a meaningful description (descriptions drive extraction quality):
```python
from pydantic import BaseModel, Field

class Publisher(BaseModel):
    name: str | None = Field(None, description="Organization that published the report")
    business_unit: str | None = Field(None, description="Research arm or institute within the organization")

class RevenueProjection(BaseModel):
    low_trillions_usd: float | None = Field(None, description="Lower bound of projected revenue, trillions USD")
    high_trillions_usd: float | None = Field(None, description="Upper bound of projected revenue, trillions USD")
    target_year: int | None = Field(None, description="Year the projection refers to")

class Arena(BaseModel):
    name: str | None = Field(None, description="Name of the arena of competition")

class ReportExtraction(BaseModel):
    title: str | None = Field(None, description="Full title of the report")
    publication_date: str | None = Field(None, description="Publication date of the report")
    publisher: Publisher = Publisher()
    revenue_projection: RevenueProjection = RevenueProjection()
    num_arenas: int | None = Field(None, description="Number of future arenas of competition identified")
    example_arenas: list[Arena] = Field(default_factory=list, description="Up to 5 arenas named in the document")
```

**loader.py**:
```python
def load_pdf(path: str) -> str
```
Open with `pymupdf.open(path)`, join page texts with "\n", truncate to `config.MAX_DOC_CHARS`, log one INFO line: pages loaded and character count. Use `logging.getLogger(__name__)`.

**tests/test_schema.py** — ReportExtraction() constructs empty; round-trip `model_validate(model_dump())`; nested fields reachable.
**tests/test_loader.py** — load the real PDF from `config.PDF_PATH` (pure local, no network): text non-empty, "arenas" in text.lower(), len(text) <= config.MAX_DOC_CHARS.

## Tests
`uv run pytest tests/ -q -m "not integration"` → green.

## Scope & constraints
- cwd: /Users/sergii/git/structured_output. Design source of truth: DESIGN.md at repo root.
- NO docstrings, NO comments. Minimal code, type hints, pydantic v2 API only.
- Touch ONLY: schema.py, loader.py, tests/test_schema.py, tests/test_loader.py.
- Do not run `fleet serve restart` or `fleet run`.

## DoD
1. Tests green.
2. `git add schema.py loader.py tests/test_schema.py tests/test_loader.py` then `git commit -m "schema and pdf loader"`.
3. Verify: `git show HEAD:schema.py | grep -c "ReportExtraction"` → ≥ 1.
4. `bd close <your-task-id> --reason "schema + loader done"`.

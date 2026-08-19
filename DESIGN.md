# structured_output — public demo of consensus-based structured extraction

A small, public, readable demo showing how to make LLM (Large Language Model) structured
output *trustworthy*: run the same extraction many times, merge the answers, count how
often each value appears (that count is the confidence score), and automatically
investigate the values the runs disagreed on.

This is a simplified public version of the private `ai_doc_classifier` project.

## What the demo shows (the story)

```
1 PDF  +  1 nested schema
        │
        ▼
  render pages         ← every PDF page becomes a PNG image (charts survive!)
        │
        ▼
  extract 10×          ← the same structured-output call (page images attached),
        │                 repeated N_RUNS times against a vision model
        │
        ▼
  merge (LLM)          ← group semantically equal values ("MGI" == "McKinsey Global Institute")
        │                 confidence = number of runs (out of 10) that produced the value
        ▼
  investigate (LLM)    ← every leaf field with confidence < 3 gets a focused
        │                 second-look call with the disagreeing candidates
        ▼
  result.json          ← final values + confidence + investigation notes
```

## Hard requirements

- **One PDF document**: `the-next-big-arenas-of-competition-executive-summary-final.pdf`
  (public McKinsey report, copied into the repo root).
- **One structured output schema with nested fields** (see `schema.py`).
- Extraction runs **10 times** against the same document.
- **Merge procedure uses an LLM** to group semantically equivalent values;
  **confidence score = number of occurrences among the 10 runs** (integer 0–10).
- **Investigation procedure** runs for every leaf field with **confidence < 3**.
- All tunable values live in **`config.py`** — nothing magic anywhere else.
- Backend: **`qwen3.8:27b` served by Ollama on the RTX server** (vision-capable).
- **The document goes to the model as page images, not extracted text** — rendering
  pages with pymupdf and attaching them via Ollama's `images` field preserves the
  information in charts, tables and layout that plain text extraction loses.
- Priorities: simplicity and readability; small, obvious abstractions; no frameworks
  (no langchain/langgraph) — just `pydantic`, `httpx`, `pymupdf`.

## config.py — the single source of truth

```python
# --- backend -----------------------------------------------------------
BASE_URL = "http://127.0.0.1:11435"   # Ollama on the RTX server (via tunnel)
MODEL = "qwen3.8:27b"
TEMPERATURE = 0.2
TIMEOUT_S = 240.0

# --- experiment --------------------------------------------------------
PDF_PATH = "the-next-big-arenas-of-competition-executive-summary-final.pdf"
N_RUNS = 10                    # how many independent extraction calls
CONFIDENCE_THRESHOLD = 3       # fields with confidence < this get investigated
RENDER_DPI = 100               # PDF page → PNG rendering resolution
CONCURRENCY = 3                # max extraction calls in flight at once

# --- output ------------------------------------------------------------
RESULT_PATH = "result.json"
```

## Repo layout — one small package, readable top-to-bottom

```
structured_output/
    src/so/
        config.py      # all constants (above)
        schema.py      # the ONE nested extraction schema (pydantic v2)
        llm.py         # one function: structured(prompt, response_model) -> model
        loader.py      # one function: render_pdf(path) -> list[str] (base64 PNGs)
        extract.py     # run the extraction prompt N_RUNS times
        merge.py       # LLM-assisted consensus merge + confidence counting
        investigate.py # second-look calls for low-confidence fields
        main.py        # pipeline: load → extract → merge → investigate → save/print
        prompts.py     # the three prompt templates as plain string functions
        __main__.py    # python -m so → main.main()
    tests/             # pytest; mocked LLM, no network needed
    pyproject.toml     # uv / PEP 621 / hatchling; deps: pydantic>=2, httpx, pymupdf
    justfile           # just run / just test / just integration
    the-next-big-arenas-...-final.pdf
    README.md
```

Flat modules inside the `so` package, no CLI framework — `uv run so`
(console script `so = "so.main:main"`, or `just run`) is the whole interface.

## schema.py — the nested schema

One pydantic model tree; nesting is the point of the demo. Every leaf carries a
`Field(description=...)` — descriptions are what the model extracts against.

```python
class Publisher(BaseModel):
    name: str | None          # "Organization that published the report"
    business_unit: str | None # "Research arm / institute within the organization"

class RevenueProjection(BaseModel):
    low_trillions_usd: float | None   # "Lower bound of projected 2040 revenue, trillions USD"
    high_trillions_usd: float | None  # "Upper bound of projected 2040 revenue, trillions USD"
    target_year: int | None           # "Year the projection refers to"

class Arena(BaseModel):
    name: str | None          # "Name of the arena of competition"

class ReportExtraction(BaseModel):   # ← the one schema of the demo
    title: str | None
    publication_date: str | None
    publisher: Publisher
    revenue_projection: RevenueProjection
    num_arenas: int | None
    example_arenas: list[Arena]      # "Up to 5 arenas named in the document"
```

### Leaf paths

Merging and confidence work on **leaf paths** — dotted field paths into the nested
structure (`publisher.name`, `revenue_projection.low_trillions_usd`, ...). One tiny
helper in `merge.py` flattens a `ReportExtraction` into `{path: value}`; lists are
flattened as a whole (the sorted list of arena names is one leaf value). This keeps
nesting in the schema while the consensus logic stays a flat, obvious dict.

## llm.py — the only I/O abstraction

```python
async def structured(prompt: str, response_model: type[T],
                     images: list[str] | None = None) -> T:
    # POST {BASE_URL}/api/chat
    # message = {"role": "user", "content": prompt}
    # if images: message["images"] = images   # base64 PNGs, one per PDF page
    # {"model": MODEL, "messages": [message],
    #  "stream": false, "format": response_model.model_json_schema(),
    #  "options": {"temperature": TEMPERATURE}}
    # parse response["message"]["content"] with model_validate_json
    # on JSON/validation error: retry once, then raise StructuredOutputError
```

That's the entire backend surface. Extraction, merge and investigation all go
through this one function.

## extract.py

```python
async def extract_n_times(pages: list[str]) -> list[ReportExtraction]:
    # N_RUNS calls of structured(extraction_prompt(), ReportExtraction, images=pages)
    # asyncio semaphore limits in-flight calls to CONCURRENCY
    # failed runs are logged and dropped; raise if ALL fail
```

## merge.py — consensus + confidence

```python
class ValueGroup(BaseModel):
    canonical_value: str | None   # best representative of the group
    count: int                    # occurrences among the runs  ← THE confidence score
    variants: list[str]           # raw distinct strings merged into this group

class MergedField(BaseModel):
    path: str                     # e.g. "publisher.name"
    value: str | None             # canonical value of the winning group
    confidence: int               # count of the winning group (0..N_RUNS)
    candidates: list[ValueGroup]  # all groups, winner first

async def merge(extractions: list[ReportExtraction]) -> list[MergedField]
```

Per leaf path:
1. Collect the value from every run (stringified; `None` for missing).
2. Exact pre-grouping: strip / casefold / collapse whitespace → identical values grouped.
3. If ≤1 distinct value → done, no LLM call.
4. Else **one** LLM call (`merge_prompt`) that clusters the distinct variants into
   semantically equivalent groups and picks the most complete variant as canonical.
   A group's count = sum of the counts of its variants. If the LLM loses or invents
   variants, fall back to the exact pre-groups (log a warning).
5. Winner = group with the highest count; `confidence = winner.count`.
   Nulls form their own group and can win (meaning: "the field is genuinely absent").

## investigate.py — second look at shaky fields

```python
class Investigation(BaseModel):
    path: str
    verdict: str | None     # the value the investigator settles on (or None)
    reasoning: str          # short explanation, quoted evidence from the document
    resolved: bool          # True if the investigator is confident in the verdict

async def investigate(pages: list[str], low_confidence: list[MergedField]) -> list[Investigation]
```

For each merged field with `confidence < CONFIDENCE_THRESHOLD`: one focused LLM call
(`investigation_prompt`) that gets the page images, the field path, and all
candidate groups with their counts, and must decide the correct value citing a verbatim
quote. Investigations run concurrently under the same semaphore.

The investigation **does not overwrite** the merged value — the final result shows the
consensus value, its confidence, and the investigation verdict side by side. That keeps
the demo honest about what each stage produced.

## main.py — the whole pipeline, readable as a script

```python
async def run() -> Result:
    pages = render_pdf(config.PDF_PATH)
    extractions = await extract_n_times(pages)
    merged = await merge(extractions)
    shaky = [f for f in merged if f.confidence < config.CONFIDENCE_THRESHOLD]
    investigations = await investigate(pages, shaky)
    return Result(document=config.PDF_PATH, n_runs=len(extractions),
                  fields=merged, investigations=investigations)
```

Prints a human-friendly table (path, value, confidence, investigated?) and writes
`result.json`.

## Testing

- Mock `llm.structured` (monkeypatch) — unit tests never touch the network.
- `test_loader.py` — real PDF, pure local: one base64 PNG per page, each decodes
  and starts with the PNG magic bytes.
- `test_extract.py` — N runs happen, partial failures tolerated, all-fail raises.
- `test_merge.py` — flattening of nested model; exact grouping; LLM-merge path with a
  scripted response; fallback when the LLM mangles variants; null-majority; confidence math.
- `test_investigate.py` — only fields under threshold are investigated.
- Integration test marked `integration`, skipped unless `RUN_INTEGRATION=1`, runs the
  real pipeline against the RTX server.
- Run: `uv run pytest -m "not integration"`.

## Conventions

- Python >= 3.11, type hints everywhere, pydantic v2 API only.
- **No docstrings, no comments** — the code must be readable on its own;
  names and small functions carry the meaning.
- Minimalistic implementation: no dead code, no speculative options, no wrappers
  around one-line stdlib calls.
- Nice logging: `logging.getLogger(__name__)` in every module; `main.py` configures
  `logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`.
  Log the story of the run: each extraction run ok/failed, each merge decision
  (exact vs LLM), each investigation started/resolved. Prints only in `main.py`.
- Every module lands together with its unit tests in the same fleet task.

## Fleet task breakdown (implementation plan)

Small, independent, simple tasks — sized for `claude:sonnet` executors. Each task
description should quote the relevant section of this document verbatim.

| # | Task | Depends on |
|---|------|-----------|
| 1 | Scaffold: pyproject.toml, config.py, copy PDF, empty modules, pytest markers | — |
| 2 | schema.py + loader.py + tests | 1 |
| 3 | llm.py (structured + retry + error) + tests | 1 |
| 4 | prompts.py (extraction / merge / investigation prompts) | 2 |
| 5 | extract.py + tests | 2, 3, 4 |
| 6 | merge.py (flatten, group, LLM merge, confidence) + tests | 5 |
| 7 | investigate.py + tests | 6 |
| 8 | main.py + result printing + README.md | 7 |
| 9 | E2E validation on the RTX server + review (simplicity/readability), file follow-up tasks | 8 |

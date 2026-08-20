# structured_output

A small demo that shows a simple trick for making LLM (Large Language Model)
structured output trustworthy: **run the same extraction many times, and count
how often each answer shows up.** If 9 out of 10 runs agree, you can trust that
field. If the runs disagree, that field gets automatically double-checked.

Structured output from an LLM is not deterministic — ask the same question
twice and you can get two different answers, even with a fixed schema. This
demo turns that instability into a feature: repetition plus counting gives you
a confidence score for free, and an automatic follow-up call resolves the
fields that scored low.

## Pipeline

```
1 PDF (17 pages → 17 PNGs)  +  1 nested schema
        │
        ▼
  extract 10×          ← the same structured-output call on the page images,
        │                 repeated N_RUNS times
        ▼
  merge (LLM)          ← flatten to leaf paths, group semantically equal values
        │                 ("MGI" == "McKinsey Global Institute")
        │                 confidence = share of runs that produced the value (0.0–1.0)
        ▼
  investigate (LLM)    ← a focused second-look call, with the disagreeing candidates,
        │                 for every leaf whose confidence < 0.3, and for every leaf where
        │                 "not found" won but some runs did find a value
        ▼
  result.json          ← final values + confidence + investigation notes
```

The pages go to the model as images, not text, so numbers that only exist inside
the exhibit charts are readable.

## What gets extracted

The schema is nested: report metadata plus **every** arena of competition in the
report, each with its 2022 revenue, its 2040 revenue range and its growth-rate
range. Consensus works on flat dotted leaf paths, and the arena list is keyed by
normalized arena name rather than list position, because runs order the arenas
differently:

```
title
publisher.name
num_arenas
arenas.cybersecurity.revenue_2022_billion_usd
arenas.cybersecurity.revenue_2040_billion_usd.low
arenas.cybersecurity.revenue_2040_billion_usd.high
arenas.cybersecurity.growth_rate_pct.low
arenas.cybersecurity.growth_rate_pct.high
...
```

Before flattening, arena names are canonicalized: an LLM call clusters spelling
variants across all runs ("electric vehicles" == "electric vehicles (evs)") so
they land under one key instead of splintering into separate low-confidence
paths. A one-off, non-arena key — e.g. a `TOTAL` row one run mistakes for an
arena — has nothing to merge into, so it stays its own low-count path and gets
investigated (and correctly comes back "not found").

See [DESIGN.md](DESIGN.md) for the full design and contracts.

## Running it

You need [uv](https://docs.astral.sh/uv/) and an [Ollama](https://ollama.com/)
server running the model configured in `src/so/config.py` (`qwen3.8:27b` by default).

```bash
uv sync
uv run so        # or: just run
```

This extracts data from the bundled PDF ten times, merges the results, prints
a table, and writes the full result to `result.json`.

## Testing

```bash
uv run pytest -m "not integration"
```

Unit tests mock the LLM, so no server is needed. The integration test runs the
real pipeline against the Ollama server:

```bash
RUN_INTEGRATION=1 uv run pytest -m integration
```

## Tweaking

Every tunable value — model name, server URL, number of runs, confidence
threshold, concurrency — lives in `config.py`.

## Sample output

A real 7-run pass over the bundled report (18 arenas, ~145 leaf paths), captured
before arena-key canonicalization landed — so it still shows the raw
spelling-variant split described above; a rerun today would fold
`arenas.electric vehicles (evs).*` into `arenas.electric vehicles.*`:

```
PATH                                                                           VALUE       CONFIDENCE  INVESTIGATED
arenas.ai software and services.revenue_2022_billion_usd                      85.0        1.00 (7/7)         -
arenas.batteries.revenue_2022_billion_usd                                     90.0        0.86 (6/7)         -
arenas.biopharmaceuticals.growth_rate_pct.high                                            0.86 (6/7)         not_found
arenas.digital advertising.growth_rate_pct.high                               24.0        0.29 (2/7)         24.0
arenas.electric vehicles (evs).revenue_2022_billion_usd                                   0.86 (6/7)         1000.0
arenas.electric vehicles.revenue_2040_billion_usd.high                        12000.0     0.29 (2/7)         13000.0
arenas.shared autonomous vehicles.growth_rate_pct.high                                    0.57 (4/7)         not found
arenas.software.growth_rate_pct.low                                                       0.86 (6/7)         17.0
num_arenas                                                                                 0.71 (5/7)         18
publication_date                                                                           0.57 (4/7)         October 2024
publisher.name                                                                McKinsey & Company  1.00 (7/7)  -
title                                                                         The next big arenas of competition  0.71 (5/7)  -
```

(full table has one row per arena × per numeric field; see `result.json` after
a run for all of them)

A few rows show the mechanism at work:

- **`num_arenas` (0.71 (5/7), investigated → 18)** — most runs left it null, but two
  runs disagreed with a value, so the null "win" gets a second look and the
  real count is recovered.
- **`arenas.electric vehicles (evs).revenue_2022_billion_usd` (0.86 (6/7), investigated
  → 1000.0)** — this is a spelling variant of `arenas.electric vehicles`
  (no `(evs)`, name-keyed as a separate arena). Only one run used this
  spelling, so its own leaves are mostly null and get investigated too.
- **`arenas.digital advertising.growth_rate_pct.high` (0.29 (2/7), investigated →
  24.0)** — genuine disagreement across runs on a number, resolved by a
  focused follow-up call.
- **`arenas.biopharmaceuticals.growth_rate_pct.high` (0.86 (6/7), investigated →
  not_found)** — investigation can also *confirm* that a value really isn't
  in the document.

One full run of the bundled 17-page PDF takes roughly half an hour on a single
RTX box: N_RUNS vision extractions at limited concurrency, then one vision
call per shaky leaf.

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
1 PDF  +  1 nested schema
        │
        ▼
  extract 10×          ← the same structured-output call, repeated N_RUNS times
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

See [DESIGN.md](DESIGN.md) for the full design and contracts.

## Running it

You need [uv](https://docs.astral.sh/uv/) and an [Ollama](https://ollama.com/)
server running the model configured in `config.py` (`qwen3.8:37b` by default).

```bash
uv sync
uv run python main.py
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

```
PATH                          VALUE                                     CONFIDENCE  INVESTIGATED
title                         The Next Big Arenas of Competition        10/10       -
publication_date              2024                                      8/10        -
publisher.name                McKinsey Global Institute                 6/10        -
publisher.business_unit       MGI                                       2/10        McKinsey Global Institute
revenue_projection.low_trillions_usd  9                                 9/10        -
num_arenas                    18                                        10/10       -
full result written to result.json
```

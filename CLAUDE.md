# structured_output

Public demo: consensus-based structured extraction from a PDF with a local LLM.
See [DESIGN.md](DESIGN.md) for the full design — it is the source of truth for
contracts, file layout, and the fleet task breakdown.

## Project goals

- Simplicity and readability above everything: flat modules inside one small
  package (`src/so/`), small obvious abstractions, no frameworks (no
  langchain/langgraph).
- All tunable values live in `src/so/config.py` only.
- Backend: `qwen3.8:27b` via Ollama on the RTX server (`http://127.0.0.1:11435`).

## Instructions

- fleet is a python orchestrator of coding agents with centralized beads db
  - documentation: `kb show fleet/add_task`
  - tasks must always be created with `--cwd /Users/sergii/git/structured_output`
  - **simple execution / coding tasks: `--coder claude --model sonnet`**
  - complex design, validation and review tasks: `--coder claude --model opus`
  - typical fleet call:
    ```
    fleet bd create --title --description --coder --model --deps --cwd
    ```
  - task descriptions must quote the relevant DESIGN.md section verbatim —
    executors do not read the whole design doc
  - each module task includes its unit tests in the same task
  - after a batch of tasks, add a finalizing task: e2e test + review for
    simplicity/readability/maintainability, which files follow-up tasks to
    fleet if needed (claude:opus)

## Commands

- run the demo: `just run` (= `uv run so`)
- run tests: `just test` (= `uv run pytest -q -m "not integration"`)
- integration test (needs RTX server): `just integration`

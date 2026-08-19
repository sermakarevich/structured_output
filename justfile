default:
    @just --list

sync:
    uv sync

run:
    uv run so

test:
    uv run pytest -q -m "not integration"

integration:
    RUN_INTEGRATION=1 uv run pytest -q -m integration

clean:
    rm -rf result.json .pytest_cache **/__pycache__

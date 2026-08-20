from pathlib import Path

from so import config

_DIR = Path(__file__).parent / config.PROMPT_VERSION


def _load(name: str) -> str:
    return (_DIR / f"{name}.txt").read_text()


def extraction_prompt() -> str:
    return _load("extraction")


def merge_prompt(path: str, variants: list[str]) -> str:
    listed = "\n".join(f"{i + 1}. {v}" for i, v in enumerate(variants))
    return _load("merge").format(path=path, listed=listed)


def investigation_prompt(path: str, candidates: list[tuple[str | None, int]]) -> str:
    listed = "\n".join(
        f"{value if value is not None else 'not found'} — {count} runs"
        for value, count in candidates
    )
    return _load("investigation").format(path=path, listed=listed)

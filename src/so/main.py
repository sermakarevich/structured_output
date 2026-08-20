import asyncio
import logging

from pydantic import BaseModel, ValidationError

from so import config
from so.ai.extract import extract_n_times
from so.ai.investigate import Investigation, investigate
from so.ai.merge import MergedField, merge
from so.data.loader import render_pdf
from so.schemas import load_schema

logger = logging.getLogger(__name__)
ReportExtraction = load_schema().ReportExtraction

NOT_FOUND_VERDICTS = {"not found", "not_found", "none", "null", ""}


class Result(BaseModel):
    document: str
    n_runs: int
    fields: list[MergedField]
    investigations: list[Investigation]


def _needs_investigation(field: MergedField) -> bool:
    if field.value is None and any(c.canonical_value is not None for c in field.candidates):
        return True
    return field.confidence < config.CONFIDENCE_THRESHOLD


async def run() -> Result:
    pages = render_pdf(config.PDF_PATH)
    extractions = await extract_n_times(pages)
    merged = await merge(extractions)
    shaky = [f for f in merged if _needs_investigation(f)]
    investigations = await investigate(pages, shaky)
    return Result(
        document=config.PDF_PATH,
        n_runs=len(extractions),
        fields=merged,
        investigations=investigations,
    )


def _verdict_value(verdict: str | None) -> str | None:
    if verdict is None or verdict.strip().casefold() in NOT_FOUND_VERDICTS:
        return None
    return verdict


def _trusted_leaves(result: Result) -> dict[str, str | None]:
    investigations = {i.path: i for i in result.investigations}
    leaves = {}
    for field in result.fields:
        investigation = investigations.get(field.path)
        if investigation is not None:
            leaves[field.path] = (
                _verdict_value(investigation.verdict) if investigation.resolved else None
            )
        else:
            leaves[field.path] = (
                field.value if field.confidence >= config.TRUST_THRESHOLD else None
            )
    return leaves


def _set_path(target: dict, path: str, value: str | None) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _unflatten(leaves: dict[str, str | None]) -> dict:
    nested: dict = {}
    arenas: dict[str, dict] = {}
    for path, value in leaves.items():
        if path.startswith("arenas."):
            _, key, rest = path.split(".", 2)
            _set_path(arenas.setdefault(key, {"name": key}), rest, value)
        else:
            _set_path(nested, path, value)
    nested["arenas"] = list(arenas.values())
    return nested


def trusted_extraction(result: Result) -> BaseModel:
    data = _unflatten(_trusted_leaves(result))
    while True:
        try:
            return ReportExtraction.model_validate(data)
        except ValidationError as e:
            for error in e.errors():
                *parents, leaf = error["loc"]
                target = data
                for part in parents:
                    target = target[part]
                logger.warning(
                    "trusted output: dropping %s (%r does not fit the schema)",
                    ".".join(str(p) for p in error["loc"]),
                    target[leaf],
                )
                target[leaf] = None


def _print_table(result: Result) -> None:
    verdicts = {i.path: i.verdict or "-" for i in result.investigations}
    path_width = max([len(f.path) for f in result.fields] + [len("PATH")]) + 2
    print(f"{'PATH'.ljust(path_width)}{'VALUE'.ljust(42)}{'CONFIDENCE'.ljust(14)}INVESTIGATED")
    for field in result.fields:
        value = (field.value or "")[:40]
        runs = round(field.confidence * result.n_runs)
        confidence = f"{field.confidence:.2f} ({runs}/{result.n_runs})"
        investigated = verdicts.get(field.path, "-")
        print(
            f"{field.path.ljust(path_width)}{value.ljust(42)}{confidence.ljust(14)}{investigated}"
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    result = asyncio.run(run())
    with open(config.RESULT_RAW_PATH, "w") as f:
        f.write(result.model_dump_json(indent=2))
    clean = trusted_extraction(result)
    with open(config.RESULT_PATH, "w") as f:
        f.write(clean.model_dump_json(indent=2))
    _print_table(result)
    print(f"trusted output written to {config.RESULT_PATH}, full detail to {config.RESULT_RAW_PATH}")


if __name__ == "__main__":
    main()

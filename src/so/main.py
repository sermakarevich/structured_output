import asyncio
import logging

from pydantic import BaseModel

from so import config
from so.extract import extract_n_times
from so.investigate import Investigation, investigate
from so.loader import render_pdf
from so.merge import MergedField, merge

logger = logging.getLogger(__name__)


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


def _print_table(result: Result) -> None:
    verdicts = {i.path: i.verdict or "-" for i in result.investigations}
    path_width = max([len(f.path) for f in result.fields] + [len("PATH")]) + 2
    print(f"{'PATH'.ljust(path_width)}{'VALUE'.ljust(42)}{'CONFIDENCE'.ljust(12)}INVESTIGATED")
    for field in result.fields:
        value = (field.value or "")[:40]
        confidence = f"{field.confidence}/{result.n_runs}"
        investigated = verdicts.get(field.path, "-")
        print(
            f"{field.path.ljust(path_width)}{value.ljust(42)}{confidence.ljust(12)}{investigated}"
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    result = asyncio.run(run())
    with open(config.RESULT_PATH, "w") as f:
        f.write(result.model_dump_json(indent=2))
    _print_table(result)
    print(f"full result written to {config.RESULT_PATH}")


if __name__ == "__main__":
    main()

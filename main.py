import asyncio
import logging

from pydantic import BaseModel

import config
from extract import extract_n_times
from investigate import Investigation, investigate
from loader import load_pdf
from merge import MergedField, merge

logger = logging.getLogger(__name__)


class Result(BaseModel):
    document: str
    n_runs: int
    fields: list[MergedField]
    investigations: list[Investigation]


async def run() -> Result:
    text = load_pdf(config.PDF_PATH)
    extractions = await extract_n_times(text)
    merged = await merge(extractions)
    shaky = [f for f in merged if f.confidence < config.CONFIDENCE_THRESHOLD]
    investigations = await investigate(text, shaky)
    return Result(
        document=config.PDF_PATH,
        n_runs=len(extractions),
        fields=merged,
        investigations=investigations,
    )


def _print_table(result: Result) -> None:
    verdicts = {i.path: i.verdict or "-" for i in result.investigations}
    header = f"{'PATH'.ljust(30)}{'VALUE'.ljust(42)}{'CONFIDENCE'.ljust(12)}INVESTIGATED"
    print(header)
    for field in result.fields:
        value = (field.value or "")[:40]
        confidence = f"{field.confidence}/{result.n_runs}"
        investigated = verdicts.get(field.path, "-")
        print(
            f"{field.path.ljust(30)}{value.ljust(42)}{confidence.ljust(12)}{investigated}"
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    result = asyncio.run(run())
    with open(config.RESULT_PATH, "w") as f:
        f.write(result.model_dump_json(indent=2))
    _print_table(result)
    print("full result written to result.json")

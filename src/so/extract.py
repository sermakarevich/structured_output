import asyncio
import logging

from so import config
from so import llm
from so.prompts import extraction_prompt
from so.schema import ReportExtraction

logger = logging.getLogger(__name__)


class AllRunsFailedError(Exception): ...


async def extract_n_times(pages: list[str]) -> list[ReportExtraction]:
    prompt = extraction_prompt()
    semaphore = asyncio.Semaphore(config.CONCURRENCY)

    async def run() -> ReportExtraction:
        async with semaphore:
            return await llm.structured(prompt, ReportExtraction, images=pages)

    results = await asyncio.gather(
        *(run() for _ in range(config.N_RUNS)), return_exceptions=True
    )

    successes = []
    for i, result in enumerate(results, start=1):
        if isinstance(result, Exception):
            logger.warning("run %d/%d failed: %s", i, config.N_RUNS, result)
        else:
            logger.info("run %d/%d ok", i, config.N_RUNS)
            successes.append(result)

    logger.info("extraction: %d/%d runs succeeded", len(successes), config.N_RUNS)
    if not successes:
        raise AllRunsFailedError(f"all {config.N_RUNS} runs failed")
    return successes

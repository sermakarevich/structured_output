import asyncio
import logging

import config
import llm
from prompts import extraction_prompt
from schema import ReportExtraction

logger = logging.getLogger(__name__)


class AllRunsFailedError(Exception): ...


async def extract_n_times(doc_text: str) -> list[ReportExtraction]:
    prompt = extraction_prompt(doc_text)
    semaphore = asyncio.Semaphore(config.CONCURRENCY)

    async def run(i: int) -> ReportExtraction:
        async with semaphore:
            return await llm.structured(prompt, ReportExtraction)

    results = await asyncio.gather(
        *(run(i) for i in range(config.N_RUNS)), return_exceptions=True
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

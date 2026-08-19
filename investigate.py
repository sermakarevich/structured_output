import asyncio
import logging

from pydantic import BaseModel

import config
import llm
import prompts
from merge import MergedField

logger = logging.getLogger(__name__)


class Investigation(BaseModel):
    path: str
    verdict: str | None
    reasoning: str
    resolved: bool


async def investigate(doc_text: str, low_confidence: list[MergedField]) -> list[Investigation]:
    if not low_confidence:
        return []

    semaphore = asyncio.Semaphore(config.CONCURRENCY)

    async def run(field: MergedField) -> Investigation:
        async with semaphore:
            logger.info("investigating %s (confidence %d)", field.path, field.confidence)
            candidates = [(g.canonical_value, g.count) for g in field.candidates]
            result = await llm.structured(
                prompts.investigation_prompt(doc_text, field.path, candidates), Investigation
            )
            result.path = field.path
            logger.info("investigated %s: resolved=%s", field.path, result.resolved)
            return result

    results = await asyncio.gather(
        *(run(field) for field in low_confidence), return_exceptions=True
    )

    investigations = []
    for field, result in zip(low_confidence, results):
        if isinstance(result, Exception):
            logger.warning("investigation of %s failed: %s", field.path, result)
        else:
            investigations.append(result)
    return investigations

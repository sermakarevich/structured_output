import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

import config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception): ...


async def _call(client: httpx.AsyncClient, prompt: str, response_model: type[T]) -> str:
    resp = await client.post(
        f"{config.BASE_URL}/api/chat",
        json={
            "model": config.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": response_model.model_json_schema(),
            "options": {"temperature": config.TEMPERATURE},
        },
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


async def structured(prompt: str, response_model: type[T]) -> T:
    logger.debug("structured call start: model=%s", response_model.__name__)
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=config.TIMEOUT_S) as client:
        content = ""
        for attempt in range(2):
            try:
                content = await _call(client, prompt, response_model)
                result = response_model.model_validate_json(content)
            except (ValidationError, ValueError) as e:
                logger.warning("structured call attempt %d failed: %s", attempt + 1, e)
                if attempt == 1:
                    raise StructuredOutputError(
                        f"{response_model.__name__}: {content[:200]}"
                    ) from e
                continue
            else:
                elapsed = time.monotonic() - start
                logger.info(
                    "structured call succeeded: model=%s elapsed=%.2fs",
                    response_model.__name__,
                    elapsed,
                )
                return result

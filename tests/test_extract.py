import asyncio

import pytest

from so import config
from so.ai import extract
from so.ai import llm
from so.schemas.arena_report import ReportExtraction

PAGES = ["img1", "img2"]


@pytest.mark.asyncio
async def test_all_succeed(monkeypatch):
    async def fake(prompt, response_model, images=None):
        assert images == PAGES
        await asyncio.sleep(0)
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    results = await extract.extract_n_times(PAGES)
    assert len(results) == config.N_RUNS


@pytest.mark.asyncio
async def test_some_fail(monkeypatch):
    counter = {"n": 0}

    async def fake(prompt, response_model, images=None):
        counter["n"] += 1
        await asyncio.sleep(0)
        if counter["n"] % 2 == 0:
            raise RuntimeError("boom")
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    results = await extract.extract_n_times(PAGES)
    assert len(results) < config.N_RUNS
    assert all(isinstance(r, ReportExtraction) for r in results)


@pytest.mark.asyncio
async def test_all_fail(monkeypatch):
    async def fake(prompt, response_model, images=None):
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    monkeypatch.setattr(llm, "structured", fake)
    with pytest.raises(extract.AllRunsFailedError):
        await extract.extract_n_times(PAGES)


@pytest.mark.asyncio
async def test_semaphore_respected(monkeypatch):
    state = {"current": 0, "max": 0}

    async def fake(prompt, response_model, images=None):
        state["current"] += 1
        state["max"] = max(state["max"], state["current"])
        await asyncio.sleep(0)
        state["current"] -= 1
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    await extract.extract_n_times(PAGES)
    assert state["max"] <= config.CONCURRENCY

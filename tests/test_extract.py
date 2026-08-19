import asyncio

import pytest

from so import config
from so import extract
from so import llm
from so.schema import ReportExtraction


@pytest.mark.asyncio
async def test_all_succeed(monkeypatch):
    async def fake(prompt, response_model):
        await asyncio.sleep(0)
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    results = await extract.extract_n_times("doc")
    assert len(results) == config.N_RUNS


@pytest.mark.asyncio
async def test_some_fail(monkeypatch):
    counter = {"n": 0}

    async def fake(prompt, response_model):
        counter["n"] += 1
        await asyncio.sleep(0)
        if counter["n"] % 2 == 0:
            raise RuntimeError("boom")
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    results = await extract.extract_n_times("doc")
    assert len(results) < config.N_RUNS
    assert all(isinstance(r, ReportExtraction) for r in results)


@pytest.mark.asyncio
async def test_all_fail(monkeypatch):
    async def fake(prompt, response_model):
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    monkeypatch.setattr(llm, "structured", fake)
    with pytest.raises(extract.AllRunsFailedError):
        await extract.extract_n_times("doc")


@pytest.mark.asyncio
async def test_semaphore_respected(monkeypatch):
    state = {"current": 0, "max": 0}

    async def fake(prompt, response_model):
        state["current"] += 1
        state["max"] = max(state["max"], state["current"])
        await asyncio.sleep(0)
        state["current"] -= 1
        return ReportExtraction()

    monkeypatch.setattr(llm, "structured", fake)
    await extract.extract_n_times("doc")
    assert state["max"] <= config.CONCURRENCY

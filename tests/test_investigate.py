import asyncio

import pytest

import investigate
import llm
from investigate import Investigation
from merge import MergedField, ValueGroup


def _field(path: str, confidence: int) -> MergedField:
    return MergedField(
        path=path,
        value="a",
        confidence=confidence,
        candidates=[
            ValueGroup(canonical_value="a", count=confidence, variants=["a"]),
            ValueGroup(canonical_value="b", count=1, variants=["b"]),
        ],
    )


@pytest.mark.asyncio
async def test_one_call_per_field_with_path_and_counts(monkeypatch):
    calls = []

    async def fake(prompt, response_model):
        calls.append(prompt)
        await asyncio.sleep(0)
        return Investigation(path="ignored", verdict="a", reasoning="r", resolved=True)

    monkeypatch.setattr(llm, "structured", fake)
    fields = [_field("title", 2), _field("summary.total", 3)]
    results = await investigate.investigate("doc", fields)

    assert len(calls) == 2
    assert "title" in calls[0]
    assert "2 runs" in calls[0]
    assert "1 runs" in calls[0]
    assert "summary.total" in calls[1]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_path_forced_to_field_path(monkeypatch):
    async def fake(prompt, response_model):
        await asyncio.sleep(0)
        return Investigation(path="wrong.path", verdict="a", reasoning="r", resolved=True)

    monkeypatch.setattr(llm, "structured", fake)
    results = await investigate.investigate("doc", [_field("title", 2)])

    assert results[0].path == "title"


@pytest.mark.asyncio
async def test_failed_investigation_dropped(monkeypatch):
    async def fake(prompt, response_model):
        await asyncio.sleep(0)
        if "title" in prompt:
            raise RuntimeError("boom")
        return Investigation(path="ignored", verdict="a", reasoning="r", resolved=True)

    monkeypatch.setattr(llm, "structured", fake)
    fields = [_field("title", 2), _field("summary.total", 3)]
    results = await investigate.investigate("doc", fields)

    assert len(results) == 1
    assert results[0].path == "summary.total"


@pytest.mark.asyncio
async def test_empty_input_no_calls(monkeypatch):
    called = False

    async def fake(prompt, response_model):
        nonlocal called
        called = True
        return Investigation(path="x", verdict=None, reasoning="", resolved=False)

    monkeypatch.setattr(llm, "structured", fake)
    results = await investigate.investigate("doc", [])

    assert results == []
    assert not called

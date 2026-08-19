import json

import pytest

import main
from investigate import Investigation
from merge import MergedField, ValueGroup
from schema import ReportExtraction


def _field(path: str, confidence: int) -> MergedField:
    return MergedField(
        path=path,
        value="v",
        confidence=confidence,
        candidates=[ValueGroup(canonical_value="v", count=confidence, variants=["v"])],
    )


@pytest.mark.asyncio
async def test_run_wires_stages_and_filters_by_threshold(monkeypatch):
    fields = [_field("title", 5), _field("publisher.name", 1)]

    async def fake_extract_n_times(text):
        assert text == "doc text"
        return [ReportExtraction(), ReportExtraction()]

    async def fake_merge(extractions):
        assert len(extractions) == 2
        return fields

    investigated_paths = []

    async def fake_investigate(text, low_confidence):
        investigated_paths.extend(f.path for f in low_confidence)
        return [Investigation(path="publisher.name", verdict="x", reasoning="r", resolved=True)]

    monkeypatch.setattr(main, "load_pdf", lambda path: "doc text")
    monkeypatch.setattr(main, "extract_n_times", fake_extract_n_times)
    monkeypatch.setattr(main, "merge", fake_merge)
    monkeypatch.setattr(main, "investigate", fake_investigate)

    result = await main.run()

    assert investigated_paths == ["publisher.name"]
    assert result.n_runs == 2
    assert result.fields == fields
    assert len(result.investigations) == 1


@pytest.mark.asyncio
async def test_result_serializes_to_json(monkeypatch):
    fields = [_field("title", 5)]

    monkeypatch.setattr(main, "load_pdf", lambda path: "doc text")
    monkeypatch.setattr(main, "extract_n_times", lambda text: _async_return([ReportExtraction()]))
    monkeypatch.setattr(main, "merge", lambda extractions: _async_return(fields))
    monkeypatch.setattr(main, "investigate", lambda text, low_confidence: _async_return([]))

    result = await main.run()
    data = json.loads(result.model_dump_json())

    assert data["n_runs"] == 1
    assert data["fields"][0]["path"] == "title"
    assert data["investigations"] == []


async def _async_return(value):
    return value

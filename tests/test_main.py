import json

import pytest

from so import main
from so.investigate import Investigation
from so.merge import MergedField, ValueGroup
from so.schemas.arena_report import ReportExtraction

PAGES = ["img1", "img2"]


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

    async def fake_extract_n_times(pages):
        assert pages == PAGES
        return [ReportExtraction(), ReportExtraction()]

    async def fake_merge(extractions):
        assert len(extractions) == 2
        return fields

    investigated_paths = []

    async def fake_investigate(pages, low_confidence):
        assert pages == PAGES
        investigated_paths.extend(f.path for f in low_confidence)
        return [Investigation(path="publisher.name", verdict="x", reasoning="r", resolved=True)]

    monkeypatch.setattr(main, "render_pdf", lambda path: PAGES)
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

    monkeypatch.setattr(main, "render_pdf", lambda path: PAGES)
    monkeypatch.setattr(main, "extract_n_times", lambda pages: _async_return([ReportExtraction()]))
    monkeypatch.setattr(main, "merge", lambda extractions: _async_return(fields))
    monkeypatch.setattr(main, "investigate", lambda pages, low_confidence: _async_return([]))

    result = await main.run()
    data = json.loads(result.model_dump_json())

    assert data["n_runs"] == 1
    assert data["fields"][0]["path"] == "title"
    assert data["investigations"] == []


@pytest.mark.asyncio
async def test_run_investigates_null_winner_with_non_null_runner_up(monkeypatch):
    field = MergedField(
        path="publication_date",
        value=None,
        confidence=7,
        candidates=[
            ValueGroup(canonical_value=None, count=7, variants=[]),
            ValueGroup(canonical_value="October 2024", count=3, variants=["October 2024"]),
        ],
    )

    investigated_paths = []

    async def fake_investigate(pages, low_confidence):
        investigated_paths.extend(f.path for f in low_confidence)
        return []

    monkeypatch.setattr(main, "render_pdf", lambda path: PAGES)
    monkeypatch.setattr(main, "extract_n_times", lambda pages: _async_return([ReportExtraction()]))
    monkeypatch.setattr(main, "merge", lambda extractions: _async_return([field]))
    monkeypatch.setattr(main, "investigate", fake_investigate)

    await main.run()

    assert investigated_paths == ["publication_date"]


@pytest.mark.asyncio
async def test_run_does_not_investigate_null_winner_when_all_candidates_null(monkeypatch):
    field = MergedField(
        path="publication_date",
        value=None,
        confidence=10,
        candidates=[ValueGroup(canonical_value=None, count=10, variants=[])],
    )

    investigated_paths = []

    async def fake_investigate(pages, low_confidence):
        investigated_paths.extend(f.path for f in low_confidence)
        return []

    monkeypatch.setattr(main, "render_pdf", lambda path: PAGES)
    monkeypatch.setattr(main, "extract_n_times", lambda pages: _async_return([ReportExtraction()]))
    monkeypatch.setattr(main, "merge", lambda extractions: _async_return([field]))
    monkeypatch.setattr(main, "investigate", fake_investigate)

    await main.run()

    assert investigated_paths == []


async def _async_return(value):
    return value

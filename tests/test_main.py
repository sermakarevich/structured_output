import json

import pytest

from so import main
from so.ai.investigate import Investigation
from so.ai.merge import MergedField, ValueGroup
from so.schemas.arena_report import ReportExtraction

PAGES = ["img1", "img2"]


def _field(path: str, confidence: float) -> MergedField:
    return MergedField(
        path=path,
        value="v",
        confidence=confidence,
        candidates=[ValueGroup(canonical_value="v", confidence=confidence, variants=["v"])],
    )


@pytest.mark.asyncio
async def test_run_wires_stages_and_filters_by_threshold(monkeypatch):
    fields = [_field("title", 0.5), _field("publisher.name", 0.1)]

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
    fields = [_field("title", 0.5)]

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
        confidence=0.7,
        candidates=[
            ValueGroup(canonical_value=None, confidence=0.7, variants=[]),
            ValueGroup(canonical_value="October 2024", confidence=0.3, variants=["October 2024"]),
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
        confidence=1.0,
        candidates=[ValueGroup(canonical_value=None, confidence=1.0, variants=[])],
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


def _result(fields, investigations=()):
    return main.Result(
        document="doc.pdf", n_runs=10, fields=fields, investigations=list(investigations)
    )


def _merged(path, value, confidence):
    groups = [ValueGroup(canonical_value=value, confidence=confidence, variants=[value] if value else [])]
    return MergedField(path=path, value=value, confidence=confidence, candidates=groups)


def test_trusted_keeps_confident_drops_shaky():
    result = _result(
        [_merged("title", "The Report", 0.9), _merged("publisher.name", "Acme", 0.4)]
    )
    clean = main.trusted_extraction(result)
    assert clean.title == "The Report"
    assert clean.publisher.name is None


def test_trusted_promotes_resolved_verdict():
    result = _result(
        [_merged("num_arenas", None, 0.6)],
        [Investigation(path="num_arenas", verdict="18", reasoning="r", resolved=True)],
    )
    clean = main.trusted_extraction(result)
    assert clean.num_arenas == 18


def test_trusted_not_found_verdict_is_null():
    result = _result(
        [_merged("title", None, 0.6)],
        [Investigation(path="title", verdict="not_found", reasoning="r", resolved=True)],
    )
    assert main.trusted_extraction(result).title is None


def test_trusted_unresolved_investigation_is_null():
    result = _result(
        [_merged("title", "Maybe", 0.9)],
        [Investigation(path="title", verdict="Maybe", reasoning="r", resolved=False)],
    )
    assert main.trusted_extraction(result).title is None


def test_trusted_rebuilds_arenas_from_paths():
    result = _result(
        [
            _merged("arenas.robotics.revenue_2022_billion_usd", "21.0", 0.9),
            _merged("arenas.robotics.growth_rate_pct.low", "13.0", 0.8),
            _merged("arenas.space.revenue_2022_billion_usd", "300.0", 0.2),
        ]
    )
    clean = main.trusted_extraction(result)
    by_name = {a.name: a for a in clean.arenas}
    assert by_name["robotics"].revenue_2022_billion_usd == 21.0
    assert by_name["robotics"].growth_rate_pct.low == 13.0
    assert by_name["space"].revenue_2022_billion_usd is None


def test_trusted_drops_verdict_that_does_not_fit_schema():
    result = _result(
        [_merged("arenas.space.revenue_2022_billion_usd", None, 0.6)],
        [
            Investigation(
                path="arenas.space.revenue_2022_billion_usd",
                verdict="around $300 billion",
                reasoning="r",
                resolved=True,
            )
        ],
    )
    clean = main.trusted_extraction(result)
    assert clean.arenas[0].revenue_2022_billion_usd is None

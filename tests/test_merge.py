import pytest
from pydantic import BaseModel

from so import merge
from so.merge import MergeGroup, MergeGroups
from so.schema import Arena, Publisher, ReportExtraction


def make_extraction(**kwargs):
    return ReportExtraction(**kwargs)


def test_flatten_all_paths():
    extraction = make_extraction(
        title="Report",
        publication_date="2024",
        publisher=Publisher(name="Org", business_unit="Research"),
        num_arenas=2,
        arenas=[
            Arena(
                name="AI",
                revenue_2022_billion_usd=10.0,
                revenue_2040_billion_usd={"low": 20.0, "high": 30.0},
                growth_rate_pct={"low": 5.0, "high": 8.0},
            ),
            Arena(name="Robotics"),
        ],
    )
    flat = merge.flatten(extraction)
    assert flat == {
        "title": "Report",
        "publication_date": "2024",
        "publisher.name": "Org",
        "publisher.business_unit": "Research",
        "num_arenas": "2",
        "arenas.ai.revenue_2022_billion_usd": "10.0",
        "arenas.ai.revenue_2040_billion_usd.low": "20.0",
        "arenas.ai.revenue_2040_billion_usd.high": "30.0",
        "arenas.ai.growth_rate_pct.low": "5.0",
        "arenas.ai.growth_rate_pct.high": "8.0",
        "arenas.robotics.revenue_2022_billion_usd": None,
        "arenas.robotics.revenue_2040_billion_usd.low": None,
        "arenas.robotics.revenue_2040_billion_usd.high": None,
        "arenas.robotics.growth_rate_pct.low": None,
        "arenas.robotics.growth_rate_pct.high": None,
    }


def test_flatten_empty_arenas_is_none():
    extraction = make_extraction()
    flat = merge.flatten(extraction)
    assert flat["title"] is None
    assert not any(k.startswith("arenas.") for k in flat)


def test_flatten_arena_name_normalized():
    a = make_extraction(arenas=[Arena(name="E-commerce ")])
    b = make_extraction(arenas=[Arena(name="e-commerce")])
    flat_a = merge.flatten(a)
    flat_b = merge.flatten(b)
    assert any(k.startswith("arenas.e-commerce.") for k in flat_a)
    assert set(flat_a.keys()) == set(flat_b.keys())


def test_flatten_null_name_arena_skipped(caplog):
    extraction = make_extraction(arenas=[Arena(name=None), Arena(name="AI")])
    flat = merge.flatten(extraction)
    assert any(k.startswith("arenas.ai.") for k in flat)
    assert len([k for k in flat if k.startswith("arenas.")]) == 5


@pytest.mark.asyncio
async def test_union_path_missing_arena_counts_as_none(monkeypatch):
    async def fake_structured(prompt, response_model):
        raise AssertionError("llm should not be called")

    monkeypatch.setattr(merge.llm, "structured", fake_structured)

    runs_with_value = [
        make_extraction(arenas=[Arena(name="robotics", revenue_2022_billion_usd=5.0)])
        for _ in range(2)
    ]
    run_without = make_extraction()
    results = await merge.merge(runs_with_value + [run_without])

    path = "arenas.robotics.revenue_2022_billion_usd"
    field = next(f for f in results if f.path == path)
    assert field.value == "5.0"
    assert field.confidence == 2
    null_group = next(g for g in field.candidates if g.canonical_value is None)
    assert null_group.count == 1


@pytest.mark.asyncio
async def test_unanimous_value_no_llm_call(monkeypatch):
    called = False

    async def fake_structured(prompt, response_model):
        nonlocal called
        called = True

    monkeypatch.setattr(merge.llm, "structured", fake_structured)

    n_runs = 5
    extractions = [make_extraction(title="Same Title") for _ in range(n_runs)]
    results = await merge.merge(extractions)

    title_field = next(f for f in results if f.path == "title")
    assert title_field.value == "Same Title"
    assert title_field.confidence == n_runs
    assert not called


@pytest.mark.asyncio
async def test_llm_clusters_variants_counts_summed(monkeypatch):
    extractions = (
        [make_extraction(title="MGI") for _ in range(6)]
        + [make_extraction(title="McKinsey Global Institute") for _ in range(4)]
    )

    async def fake_structured(prompt, response_model):
        return MergeGroups(
            groups=[
                MergeGroup(
                    canonical_value="McKinsey Global Institute",
                    variants=["MGI", "McKinsey Global Institute"],
                )
            ]
        )

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    title_field = next(f for f in results if f.path == "title")
    assert title_field.value == "McKinsey Global Institute"
    assert title_field.confidence == 10
    assert len(title_field.candidates) == 1


@pytest.mark.asyncio
async def test_llm_missing_variant_falls_back_to_exact(monkeypatch):
    extractions = (
        [make_extraction(title="A") for _ in range(3)]
        + [make_extraction(title="B") for _ in range(2)]
    )

    async def fake_structured(prompt, response_model):
        return MergeGroups(groups=[MergeGroup(canonical_value="A", variants=["A"])])

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    title_field = next(f for f in results if f.path == "title")
    assert title_field.value == "A"
    assert title_field.confidence == 3
    assert len(title_field.candidates) == 2


@pytest.mark.asyncio
async def test_null_majority_wins_with_none_canonical(monkeypatch):
    extractions = (
        [make_extraction(title=None) for _ in range(6)]
        + [make_extraction(title="Something") for _ in range(4)]
    )

    async def fake_structured(prompt, response_model):
        raise AssertionError("llm should not be called when only one non-null group exists")

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    title_field = next(f for f in results if f.path == "title")
    assert title_field.value is None
    assert title_field.confidence == 6


@pytest.mark.asyncio
async def test_arena_name_variants_canonicalized(monkeypatch):
    extractions = (
        [
            make_extraction(arenas=[Arena(name="electric vehicles", revenue_2022_billion_usd=5.0)])
            for _ in range(7)
        ]
        + [
            make_extraction(
                arenas=[Arena(name="electric vehicles (evs)", revenue_2022_billion_usd=5.0)]
            )
            for _ in range(3)
        ]
    )

    async def fake_structured(prompt, response_model):
        assert response_model is merge.MergeGroups
        return MergeGroups(
            groups=[
                MergeGroup(
                    canonical_value="electric vehicles",
                    variants=["electric vehicles", "electric vehicles (evs)"],
                )
            ]
        )

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    path = "arenas.electric vehicles.revenue_2022_billion_usd"
    field = next(f for f in results if f.path == path)
    assert field.value == "5.0"
    assert field.confidence == 10
    assert not any(f.path.startswith("arenas.electric vehicles (evs)") for f in results)


@pytest.mark.asyncio
async def test_arena_name_llm_mismatch_falls_back_to_raw_keys(monkeypatch):
    extractions = [
        make_extraction(arenas=[Arena(name="software", revenue_2022_billion_usd=1.0)])
        for _ in range(6)
    ] + [
        make_extraction(
            arenas=[Arena(name="ai software and services", revenue_2022_billion_usd=1.0)]
        )
        for _ in range(4)
    ]

    async def fake_structured(prompt, response_model):
        return MergeGroups(groups=[MergeGroup(canonical_value="software", variants=["software"])])

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    assert any(f.path.startswith("arenas.software.") for f in results)
    assert any(f.path.startswith("arenas.ai software and services.") for f in results)


@pytest.mark.asyncio
async def test_single_arena_name_skips_llm(monkeypatch):
    async def fake_structured(prompt, response_model):
        raise AssertionError("llm should not be called for a single arena name")

    monkeypatch.setattr(merge.llm, "structured", fake_structured)

    extractions = [
        make_extraction(arenas=[Arena(name="AI", revenue_2022_billion_usd=1.0)]) for _ in range(5)
    ]
    results = await merge.merge(extractions)
    assert any(f.path.startswith("arenas.ai.") for f in results)


@pytest.mark.asyncio
async def test_confidence_math_split(monkeypatch):
    extractions = (
        [make_extraction(title="X") for _ in range(6)]
        + [make_extraction(title="Y") for _ in range(4)]
    )

    async def fake_structured(prompt, response_model):
        return MergeGroups(
            groups=[
                MergeGroup(canonical_value="X", variants=["X"]),
                MergeGroup(canonical_value="Y", variants=["Y"]),
            ]
        )

    monkeypatch.setattr(merge.llm, "structured", fake_structured)
    results = await merge.merge(extractions)

    title_field = next(f for f in results if f.path == "title")
    assert title_field.confidence == 6
    assert title_field.value == "X"

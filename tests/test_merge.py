import pytest
from pydantic import BaseModel

from so import merge
from so.merge import MergeGroup, MergeGroups
from so.schema import Arena, Publisher, ReportExtraction, RevenueProjection


def make_extraction(**kwargs):
    return ReportExtraction(**kwargs)


def test_flatten_all_paths():
    extraction = make_extraction(
        title="Report",
        publication_date="2024",
        publisher=Publisher(name="Org", business_unit="Research"),
        revenue_projection=RevenueProjection(low_trillions_usd=1.0, high_trillions_usd=2.0, target_year=2030),
        num_arenas=2,
        example_arenas=[Arena(name="AI"), Arena(name="Robotics")],
    )
    flat = merge.flatten(extraction)
    assert flat == {
        "title": "Report",
        "publication_date": "2024",
        "publisher.name": "Org",
        "publisher.business_unit": "Research",
        "revenue_projection.low_trillions_usd": "1.0",
        "revenue_projection.high_trillions_usd": "2.0",
        "revenue_projection.target_year": "2030",
        "num_arenas": "2",
        "example_arenas": "AI, Robotics",
    }


def test_flatten_empty_arenas_is_none():
    extraction = make_extraction()
    flat = merge.flatten(extraction)
    assert flat["example_arenas"] is None
    assert flat["title"] is None


def test_flatten_generic_list_field_of_scalars_and_models():
    class Tag(BaseModel):
        label: str | None = None

    class WithLists(BaseModel):
        tags: list[str] = []
        entries: list[Tag] = []

    model = WithLists(tags=["b", "a", "b"], entries=[Tag(label="Y"), Tag(label="X"), Tag(label=None)])
    flat = merge.flatten(model)
    assert flat["tags"] == "a, b, b"
    assert flat["entries"] == "X, Y"

    empty = WithLists()
    flat_empty = merge.flatten(empty)
    assert flat_empty["tags"] is None
    assert flat_empty["entries"] is None


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

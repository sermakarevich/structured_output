import asyncio

import pytest

import config
import main

LEAF_PATHS = {
    "title",
    "publication_date",
    "publisher.name",
    "publisher.business_unit",
    "revenue_projection.low_trillions_usd",
    "revenue_projection.high_trillions_usd",
    "revenue_projection.target_year",
    "num_arenas",
    "example_arenas",
}


@pytest.mark.integration
def test_pipeline_against_real_backend():
    result = asyncio.run(main.run())

    assert {f.path for f in result.fields} == LEAF_PATHS
    assert result.n_runs >= 8
    title = next(f for f in result.fields if f.path == "title")
    assert title.confidence >= 6
    for field in result.fields:
        if field.confidence < config.CONFIDENCE_THRESHOLD:
            assert any(i.path == field.path for i in result.investigations)

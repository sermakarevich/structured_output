import asyncio

import pytest

from so import config
from so import main

SCALAR_LEAF_PATHS = {
    "title",
    "publication_date",
    "publisher.name",
    "publisher.business_unit",
    "num_arenas",
}


@pytest.mark.integration
def test_pipeline_against_real_backend():
    result = asyncio.run(main.run())

    paths = {f.path for f in result.fields}
    assert SCALAR_LEAF_PATHS <= paths
    assert result.n_runs >= 8

    arena_keys = {p.split(".")[1] for p in paths if p.startswith("arenas.")}
    assert len(arena_keys) >= 10

    num_arenas = next(f for f in result.fields if f.path == "num_arenas")
    assert num_arenas.value is not None
    assert 15 <= float(num_arenas.value) <= 21

    revenue_2040 = {
        f.path: f.value for f in result.fields if ".revenue_2040_billion_usd." in f.path
    }
    assert any(
        revenue_2040.get(f"arenas.{key}.revenue_2040_billion_usd.low") is not None
        and revenue_2040.get(f"arenas.{key}.revenue_2040_billion_usd.high") is not None
        for key in arena_keys
    )

    title = next(f for f in result.fields if f.path == "title")
    assert title.confidence >= 6
    for field in result.fields:
        if field.confidence < config.CONFIDENCE_THRESHOLD:
            assert any(i.path == field.path for i in result.investigations)

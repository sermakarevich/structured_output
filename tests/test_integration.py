import asyncio
import os

import pytest

from so import config
from so import main

SCALAR_LEAF_PATHS = {
    "title",
    "publisher.name",
    "publisher.publication_date",
    "num_arenas",
}


pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION"), reason="needs RUN_INTEGRATION=1 and the RTX server"
)


@pytest.mark.integration
def test_pipeline_against_real_backend():
    result = asyncio.run(main.run())

    paths = {f.path for f in result.fields}
    assert SCALAR_LEAF_PATHS <= paths
    assert result.n_runs >= 8

    arena_keys = {p.split(".")[1] for p in paths if p.startswith("arenas.")}
    assert len(arena_keys) >= 10

    num_arenas = next(f for f in result.fields if f.path == "num_arenas")
    if num_arenas.value is not None:
        assert float(num_arenas.value) == 18
    else:
        assert any(i.path == "num_arenas" for i in result.investigations)

    revenue_2040 = {
        f.path: f.value for f in result.fields if ".revenue_2040_billion_usd." in f.path
    }
    assert any(
        revenue_2040.get(f"arenas.{key}.revenue_2040_billion_usd.low") is not None
        and revenue_2040.get(f"arenas.{key}.revenue_2040_billion_usd.high") is not None
        for key in arena_keys
    )

    title = next(f for f in result.fields if f.path == "title")
    assert title.confidence >= 0.6

    clean = main.trusted_extraction(result)
    assert clean.title is not None
    assert any(a.revenue_2022_billion_usd is not None for a in clean.arenas)
    for field in result.fields:
        if field.confidence < config.CONFIDENCE_THRESHOLD:
            assert any(i.path == field.path for i in result.investigations)

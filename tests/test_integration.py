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
    assert any(p.startswith("arenas.") for p in paths)
    assert result.n_runs >= 8
    title = next(f for f in result.fields if f.path == "title")
    assert title.confidence >= 6
    for field in result.fields:
        if field.confidence < config.CONFIDENCE_THRESHOLD:
            assert any(i.path == field.path for i in result.investigations)

from so.schemas.arena_report import ReportExtraction


def test_empty_construct():
    model = ReportExtraction()
    assert model.title is None
    assert model.publisher.name is None
    assert model.arenas == []


def test_round_trip():
    model = ReportExtraction(
        title="Report",
        num_arenas=2,
        arenas=[
            {
                "name": "AI",
                "revenue_2022_billion_usd": 10.0,
                "revenue_2040_billion_usd": {"low": 20.0, "high": 30.0},
                "growth_rate_pct": {"low": 5.0, "high": 8.0},
            },
            {"name": "Robotics"},
        ],
    )
    restored = ReportExtraction.model_validate(model.model_dump())
    assert restored == model


def test_nested_fields_reachable():
    model = ReportExtraction(
        publisher={"name": "Org", "business_unit": "Research"},
        arenas=[
            {
                "name": "AI",
                "revenue_2022_billion_usd": 10.0,
                "revenue_2040_billion_usd": {"low": 20.0, "high": 30.0},
                "growth_rate_pct": {"low": 5.0, "high": 8.0},
            }
        ],
    )
    assert model.publisher.name == "Org"
    assert model.publisher.business_unit == "Research"
    arena = model.arenas[0]
    assert arena.revenue_2022_billion_usd == 10.0
    assert arena.revenue_2040_billion_usd.low == 20.0
    assert arena.revenue_2040_billion_usd.high == 30.0
    assert arena.growth_rate_pct.low == 5.0
    assert arena.growth_rate_pct.high == 8.0

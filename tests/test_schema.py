from so.schema import ReportExtraction


def test_empty_construct():
    model = ReportExtraction()
    assert model.title is None
    assert model.publisher.name is None
    assert model.revenue_projection.low_trillions_usd is None
    assert model.example_arenas == []


def test_round_trip():
    model = ReportExtraction(
        title="Report",
        num_arenas=2,
        example_arenas=[{"name": "AI"}, {"name": "Robotics"}],
    )
    restored = ReportExtraction.model_validate(model.model_dump())
    assert restored == model


def test_nested_fields_reachable():
    model = ReportExtraction(
        publisher={"name": "Org", "business_unit": "Research"},
        revenue_projection={"low_trillions_usd": 1.0, "high_trillions_usd": 2.0, "target_year": 2030},
    )
    assert model.publisher.name == "Org"
    assert model.publisher.business_unit == "Research"
    assert model.revenue_projection.target_year == 2030

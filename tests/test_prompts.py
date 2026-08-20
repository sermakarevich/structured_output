from so.prompts import extraction_prompt, investigation_prompt, merge_prompt


def test_extraction_prompt():
    result = extraction_prompt()
    assert isinstance(result, str)
    assert result
    assert "image" in result.lower()


def test_merge_prompt():
    variants = ["MGI", "McKinsey Global Institute", "McKinsey"]
    result = merge_prompt("publisher.name", variants)
    assert isinstance(result, str)
    assert result
    assert "publisher.name" in result
    for variant in variants:
        assert variant in result


def test_investigation_prompt():
    candidates = [("29-48 trillion USD", 0.4), (None, 0.2)]
    result = investigation_prompt("revenue_projection.high_trillions_usd", candidates)
    assert isinstance(result, str)
    assert result
    assert "revenue_projection.high_trillions_usd" in result
    assert "29-48 trillion USD" in result
    assert "40% of runs" in result
    assert "not found" in result
    assert "20% of runs" in result

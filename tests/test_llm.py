import httpx
import pytest
from pydantic import BaseModel

from so import config
from so import llm


class Item(BaseModel):
    name: str
    count: int


def make_handler(responses):
    calls = []

    def handler(request):
        calls.append(request)
        body = responses[len(calls) - 1]
        return httpx.Response(200, json={"message": {"content": body}})

    return handler, calls


@pytest.mark.asyncio
async def test_happy_path(monkeypatch):
    handler, calls = make_handler(['{"name": "a", "count": 1}'])

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    result = await llm.structured("prompt", Item)
    assert result == Item(name="a", count=1)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retry_then_succeed(monkeypatch):
    handler, calls = make_handler(["not json", '{"name": "b", "count": 2}'])

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    result = await llm.structured("prompt", Item)
    assert result == Item(name="b", count=2)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_fails_twice_raises(monkeypatch):
    handler, calls = make_handler(["not json"] * config.MAX_ATTEMPTS)

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    with pytest.raises(llm.StructuredOutputError):
        await llm.structured("prompt", Item)
    assert len(calls) == config.MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_request_contains_schema(monkeypatch):
    handler, calls = make_handler(['{"name": "a", "count": 1}'])

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    await llm.structured("prompt", Item)
    sent = calls[0].content
    import json

    body = json.loads(sent)
    assert body["format"] == Item.model_json_schema()


@pytest.mark.asyncio
async def test_images_included_when_passed(monkeypatch):
    handler, calls = make_handler(['{"name": "a", "count": 1}'])

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    await llm.structured("prompt", Item, images=["abc"])
    import json

    body = json.loads(calls[0].content)
    assert body["messages"][0]["images"] == ["abc"]


@pytest.mark.asyncio
async def test_images_omitted_when_not_passed(monkeypatch):
    handler, calls = make_handler(['{"name": "a", "count": 1}'])

    orig_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)

    await llm.structured("prompt", Item)
    import json

    body = json.loads(calls[0].content)
    assert "images" not in body["messages"][0]

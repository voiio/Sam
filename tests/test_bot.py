import io
from collections import namedtuple
from unittest import mock

import httpx
import pytest
import respx
from sam import bot


@pytest.fixture
def client(monkeypatch):
    client = mock.AsyncMock()
    monkeypatch.setattr("openai.AsyncOpenAI", mock.Mock(return_value=client))
    return client


@pytest.mark.asyncio
async def test_tts(client):
    with io.BytesIO() as ts:
        ts.write(b"Hello")
        ts.seek(0)
        client.audio.speech.create.return_value = ts
        assert await bot.tts("Hello") == b"Hello"


@pytest.mark.asyncio
async def test_stt(client):
    client.audio.transcriptions.create.return_value = namedtuple(
        "Transcription", ["text"]
    )(text="Hello")
    assert await bot.stt(b"Hello") == "Hello"


@respx.mock
@pytest.mark.asyncio
async def test_get_tool_ids_success(monkeypatch):
    """Test get_tool_ids returns correct tool IDs on successful response."""
    monkeypatch.setattr("sam.config.OPEN_WEBUI_URL", "https://example.com")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_API_KEY", "valid-key")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_MODEL", "test-model")

    respx.get("https://example.com/api/models").respond(
        json={
            "data": [
                {"id": "test-model", "info": {"meta": {"toolIds": ["tool1", "tool2"]}}},
                {"id": "other-model", "info": {"meta": {"toolIds": ["tool3"]}}},
            ]
        }
    )

    result = await bot.get_tool_ids()
    assert result == ["tool1", "tool2"]


@respx.mock
@pytest.mark.asyncio
async def test_get_tool_ids_http_error(monkeypatch):
    """Test get_tool_ids returns empty list on HTTP error."""
    monkeypatch.setattr("sam.config.OPEN_WEBUI_URL", "https://example.com")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_API_KEY", "valid-key")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_MODEL", "test-model")

    respx.get("https://example.com/api/models").respond(401)

    result = await bot.get_tool_ids()
    assert result == []


@respx.mock
@pytest.mark.asyncio
async def test_get_tool_ids_missing_data_key(monkeypatch):
    """Test get_tool_ids returns empty list when 'data' key is missing."""
    monkeypatch.setattr("sam.config.OPEN_WEBUI_URL", "https://example.com")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_API_KEY", "valid-key")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_MODEL", "test-model")

    respx.get("https://example.com/api/models").respond(json={"error": "some error"})

    result = await bot.get_tool_ids()
    assert result == []


@respx.mock
@pytest.mark.asyncio
async def test_get_tool_ids_model_not_found(monkeypatch):
    """Test get_tool_ids returns empty list when model is not found."""
    monkeypatch.setattr("sam.config.OPEN_WEBUI_URL", "https://example.com")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_API_KEY", "valid-key")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_MODEL", "missing-model")

    respx.get("https://example.com/api/models").respond(
        json={"data": [{"id": "other-model", "info": {"meta": {"toolIds": ["tool1"]}}}]}
    )

    result = await bot.get_tool_ids()
    assert result == []


@pytest.mark.asyncio
async def test_get_tool_ids_network_error(monkeypatch):
    """Test get_tool_ids returns empty list on network error."""
    monkeypatch.setattr("sam.config.OPEN_WEBUI_URL", "https://example.com")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_API_KEY", "valid-key")
    monkeypatch.setattr("sam.config.OPEN_WEBUI_MODEL", "test-model")

    # Mock httpx.AsyncClient to raise a RequestError
    async def mock_get(*args, **kwargs):
        raise httpx.RequestError("Network error")

    with mock.patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = mock_get

        result = await bot.get_tool_ids()
        assert result == []


@pytest.mark.asyncio
async def test_get_tool_ids_missing_config():
    """Test get_tool_ids returns empty list when config is missing."""
    with mock.patch("sam.config.OPEN_WEBUI_URL", None):
        result = await bot.get_tool_ids()
        assert result == []

    with mock.patch("sam.config.OPEN_WEBUI_API_KEY", None):
        result = await bot.get_tool_ids()
        assert result == []

    with mock.patch("sam.config.OPEN_WEBUI_MODEL", None):
        result = await bot.get_tool_ids()
        assert result == []

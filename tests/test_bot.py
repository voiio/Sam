import io
from collections import namedtuple
from unittest import mock

import pytest
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

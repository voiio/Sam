from collections import namedtuple
from unittest import mock

import pytest
from openai.types.beta.threads import Message, Text, TextContentBlock

from sam import bot


@pytest.fixture
def client(monkeypatch):
    client = mock.AsyncMock()
    monkeypatch.setattr("openai.AsyncOpenAI", mock.Mock(return_value=client))
    return client


@pytest.mark.asyncio
async def test_complete_run__max_retries(client):
    client.beta.threads.runs.cancel = mock.AsyncMock()
    with pytest.raises(RecursionError):
        await bot.complete_run(run_id="run-1", thread_id="thread-1", retry=11)
    assert client.beta.threads.runs.cancel.called
    assert client.beta.threads.runs.cancel.call_args[1]["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_complete_run__requires_action(client, monkeypatch):
    web_search = mock.AsyncMock()
    monkeypatch.setattr("sam.tools.web_search", web_search)
    required_action = mock.Mock()
    tool_call = mock.Mock()
    tool_call.function.arguments = "{}"
    tool_call.function.name = "web_search"
    required_action.submit_tool_outputs.tool_calls = [tool_call]
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status", "required_action"]
    )(id="run-1", status="requires_action", required_action=required_action)
    with pytest.raises(RecursionError):
        await bot.complete_run(run_id="run-1", thread_id="thread-1")
    assert web_search.called


@pytest.mark.asyncio
async def test_complete_run__queued(monkeypatch, client):
    monkeypatch.setattr("sam.utils.backoff", mock.AsyncMock())
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status"]
    )(id="run-1", status="queued")
    with pytest.raises(Exception) as e:
        await bot.complete_run(run_id="run-1", thread_id="thread-1")

    assert "Max retries exceeded" in str(e.value)


@pytest.mark.asyncio
async def test_run(monkeypatch, client):
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status"]
    )(id="run-1", status="queued")
    client.beta.threads.messages.list.return_value = namedtuple("Response", ["data"])(
        data=[
            Message(
                id="msg-1",
                content=[
                    TextContentBlock(
                        type="text", text=Text(value="Hello", annotations=[])
                    )
                ],
                status="completed",
                role="assistant",
                created_at=123,
                files=[],
                file_ids=[],
                object="thread.message",
                thread_id="thread-4",
            ),
        ]
    )
    bot.complete_run = mock.AsyncMock()
    await bot.run(thread_id="thread-1", assistant_id="assistant-1")
    assert bot.complete_run.called

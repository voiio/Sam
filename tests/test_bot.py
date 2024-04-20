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
async def test_add_message(client):
    assert await bot.add_message("thread-1", "Hello", []) == (False, False)
    assert client.beta.threads.messages.create.called
    assert client.beta.threads.messages.create.call_args == mock.call(
        thread_id="thread-1", content="Hello", role="user", attachments=[]
    )


@pytest.mark.asyncio
async def test_add_message__file(client):
    client.files.create.return_value = namedtuple("File", ["id"])(id="file-123")
    assert await bot.add_message("thread-1", "Hello", [("file-1", b"Hello")]) == (
        True,
        False,
    )
    assert client.beta.threads.messages.create.called
    assert client.beta.threads.messages.create.call_args == mock.call(
        thread_id="thread-1",
        content="Hello",
        role="user",
        attachments=[{"file_id": "file-123", "tools": [{"type": "file_search"}]}],
    )


@pytest.mark.asyncio
async def test_add_message__audio(client):
    client.audio.transcriptions.create.return_value = namedtuple(
        "Transcription", ["text"]
    )(text="World")
    assert await bot.add_message("thread-1", "Hello", [("file-1.mp3", b"World")]) == (
        False,
        True,
    )
    assert client.beta.threads.messages.create.call_args == mock.call(
        thread_id="thread-1", content="Hello\nWorld", role="user", attachments=[]
    )


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
        "Run", ["id", "thread_id", "status", "required_action"]
    )(
        id="run-1",
        thread_id="thread-1",
        status="requires_action",
        required_action=required_action,
    )
    with pytest.raises(RecursionError):
        await bot.complete_run(run_id="run-1", thread_id="thread-1")
    assert web_search.called


@pytest.mark.asyncio
async def test_complete_run__queued(monkeypatch, client):
    monkeypatch.setattr("sam.utils.backoff", mock.AsyncMock())
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status"]
    )(id="run-1", status="queued")
    with pytest.raises(RecursionError) as e:
        await bot.complete_run(run_id="run-1", thread_id="thread-1")

    assert "Max retries exceeded" in str(e.value)


@pytest.mark.asyncio
async def test_complete_run__completed(monkeypatch, client):
    monkeypatch.setattr("sam.utils.backoff", mock.AsyncMock())
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status"]
    )(id="run-1", status="completed")
    await bot.complete_run(run_id="run-1", thread_id="thread-1")


@pytest.mark.asyncio
async def test_complete_run__unexpected_status(monkeypatch, client):
    monkeypatch.setattr("sam.utils.backoff", mock.AsyncMock())
    client.beta.threads.runs.retrieve.return_value = namedtuple(
        "Run", ["id", "status"]
    )(id="run-1", status="failed")
    with pytest.raises(IOError):
        await bot.complete_run(run_id="run-1", thread_id="thread-1")


@pytest.mark.asyncio
async def test_execute_run(monkeypatch, client):
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
    complete_run = mock.AsyncMock()
    monkeypatch.setattr(bot, "complete_run", complete_run)
    await bot.execute_run(thread_id="thread-1", assistant_id="assistant-1")
    assert complete_run.called


@pytest.mark.asyncio
async def test_execute_run__no_completed(monkeypatch, client):
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
    complete_run = mock.AsyncMock(side_effect=[RecursionError, None])
    monkeypatch.setattr(bot, "complete_run", complete_run)
    response = await bot.execute_run(thread_id="thread-1", assistant_id="assistant-1")
    assert complete_run.called
    assert response == "🤯"


@pytest.mark.asyncio
async def test_execute_run__no_message(monkeypatch, client):
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
    complete_run = mock.AsyncMock()
    monkeypatch.setattr(bot, "complete_run", complete_run)
    fetch_latest_assistant_message = mock.AsyncMock(side_effect=[ValueError, None])
    monkeypatch.setattr(
        bot, "fetch_latest_assistant_message", fetch_latest_assistant_message
    )
    response = await bot.execute_run(thread_id="thread-1", assistant_id="assistant-1")
    assert complete_run.called
    assert fetch_latest_assistant_message.called
    assert response == "🤯"

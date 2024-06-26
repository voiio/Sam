import io
from collections import namedtuple
from unittest import mock

import pytest
from openai import BadRequestError
from openai.types.beta.threads import (
    ImageFile,
    ImageFileContentBlock,
    Message,
    Text,
    TextContentBlock,
)
from sam import bot, config


@pytest.fixture
def client(monkeypatch):
    client = mock.AsyncMock()
    monkeypatch.setattr("openai.AsyncOpenAI", mock.Mock(return_value=client))
    return client


class TestRunError:
    def test_msg(self):
        run_error = bot.RunError(run=namedtuple("Run", ["status"])("failed"))
        assert str(run_error) == "Run failed"


class TestIncompleteRunError:
    def test_msg(self):
        run_error = bot.IncompleteRunError(
            run=namedtuple("Run", ["status", "incomplete_details"])(
                "failed",
                namedtuple("IncompleteDetails", ["reason"])("max_tokens_exceeded"),
            )
        )
        assert str(run_error) == "Run failed: max_tokens_exceeded"


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
async def test_add_message__bad_request(client):
    client.beta.threads.messages.create.side_effect = BadRequestError(
        response=mock.Mock(), message="Bad request", body={"message": "Bad Request"}
    )
    with pytest.raises(OSError):
        await bot.add_message("thread-1", "", [])


@pytest.mark.asyncio
async def test_call_tools__value_error(client):
    run = mock.MagicMock()
    run.required_action = None
    with pytest.raises(ValueError):
        await bot.call_tools(run)


@pytest.mark.asyncio
async def test_call_tools__io_error_fn_name(client):
    run = mock.MagicMock()
    tool_call = mock.MagicMock()
    tool_call.function.name = "does_no_exist"
    run.required_action.submit_tool_outputs.tool_calls = [tool_call]
    with pytest.raises(OSError) as e:
        await bot.call_tools(run)
    assert "Tool does_no_exist not found" in str(e.value)


@pytest.mark.asyncio
async def test_call_tools__type_error_fn_kwargs(client):
    run = mock.MagicMock()
    tool_call = mock.MagicMock()
    tool_call.function.name = "web_search"
    tool_call.function.arguments = "{'notJSON'}"
    run.required_action.submit_tool_outputs.tool_calls = [tool_call]
    with pytest.raises(TypeError) as e:
        await bot.call_tools(run)
    assert "Object of type set is not JSON serializable" in str(e.value)


@pytest.mark.asyncio
async def test_call_tools__exception(client):
    run = mock.MagicMock()
    tool_call = mock.MagicMock()
    tool_call.function.name = "web_search"
    tool_call.function.arguments = '{"wrong": "args"}'
    run.required_action.submit_tool_outputs.tool_calls = [tool_call]
    with pytest.raises(OSError) as e:
        await bot.call_tools(run)
    assert "Tool web_search failed, cancelling run" in str(e.value)


@pytest.mark.asyncio
async def test_complete_run__max_retries(client):
    client.beta.threads.runs.cancel = mock.AsyncMock()
    with pytest.raises(RecursionError):
        await bot.complete_run(run_id="run-1", thread_id="thread-1", retry=11)
    assert client.beta.threads.runs.cancel.called
    assert client.beta.threads.runs.cancel.call_args[1]["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_complete_run__requires_action(client, monkeypatch):
    web_search = mock.Mock()
    config.TOOLS["web_search"] = web_search
    required_action = mock.Mock()
    tool_call = mock.Mock()
    tool_call.function.arguments = '{"query": "ferien"}'
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
    config.TOOLS = dict(config.load_tools())
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
    with pytest.raises(OSError):
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
async def test_execute_run_with_files(monkeypatch, client):
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
    await bot.execute_run(
        thread_id="thread-1", assistant_id="assistant-1", file_search=True
    )
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


@pytest.mark.asyncio
async def test_get_thread_id(client):
    client.beta.threads.create.return_value = namedtuple("Thread", ["id"])(
        id="thread-1"
    )
    assert await bot.get_thread_id("channel-1") == "thread-1"
    assert await bot.get_thread_id("channel-1") == "thread-1"


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


@pytest.mark.asyncio
async def test_fetch_latest_assistant_message(client):
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
    assert await bot.fetch_latest_assistant_message("thread-1") == "Hello"


@pytest.mark.asyncio
async def test_fetch_latest_assistant_message__value_error(client):
    client.beta.threads.messages.list.return_value = namedtuple("Response", ["data"])(
        data=[
            Message(
                id="msg-1",
                content=[
                    ImageFileContentBlock(
                        type="image_file",
                        image_file=ImageFile(
                            file_id="file-1",
                        ),
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
    with pytest.raises(ValueError) as e:
        assert await bot.fetch_latest_assistant_message("thread-1") == "Hello"
    assert "No assistant message found" in str(e.value)


@pytest.mark.asyncio
async def test_fetch_latest_assistant_message__empty(client):
    client.beta.threads.messages.list.return_value = namedtuple("Response", ["data"])(
        data=[
            Message(
                id="msg-1",
                content=[],
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
    with pytest.raises(ValueError) as e:
        assert await bot.fetch_latest_assistant_message("thread-1") == "Hello"
    assert "No assistant message found" in str(e.value)

import logging
from unittest import mock

import pytest
import respx
from sam import bot, slack


@pytest.mark.asyncio
async def test_get_bot_user_id(monkeypatch):
    auth_test = mock.AsyncMock(return_value={"user_id": "bot-1"})
    monkeypatch.setattr(slack.AsyncWebClient, "auth_test", auth_test)
    assert await slack.get_bot_user_id() == "bot-1"
    assert auth_test.called


@respx.mock
@pytest.mark.asyncio
async def test_handle_message(monkeypatch):
    respx.get("https://example.com/file.mp3").respond(content=b"Hello")
    add_message = mock.AsyncMock(return_value=(["file-1"], False))
    monkeypatch.setattr(bot, "add_message", add_message)
    send_response = mock.AsyncMock()
    monkeypatch.setattr(slack, "send_response", send_response)
    get_bot_user_id = mock.AsyncMock(return_value="bot-1")
    monkeypatch.setattr(slack, "get_bot_user_id", get_bot_user_id)
    monkeypatch.setattr(
        "sam.bot.get_thread",
        mock.AsyncMock(return_value={"model": "gpt-4o-mini", "messages": []}),
    )
    say = mock.AsyncMock()
    event = {
        "channel": "channel-1",
        "client_msg_id": "client-msg-1",
        "channel_type": "im",
        "user": "user-1",
        "text": "Hello",
        "files": [
            {
                "url_private": "https://example.com/file.mp3",
                "name": "file.mp3",
            }
        ],
    }
    await slack.handle_message(event, say)
    assert add_message.called
    assert send_response.called
    assert send_response.call_args == mock.call(
        {
            "channel": "channel-1",
            "client_msg_id": "client-msg-1",
            "channel_type": "im",
            "user": "user-1",
            "text": "Hello",
            "files": [
                {"url_private": "https://example.com/file.mp3", "name": "file.mp3"}
            ],
        },
        say,
        voice_response=False,
    )


@pytest.mark.asyncio
async def test_handle_message__subtype_deleted(caplog):
    event = {
        "type": "message",
        "subtype": "message_deleted",
        "hidden": True,
        "channel": "C123ABC456",
        "ts": "1358878755.000001",
        "deleted_ts": "1358878749.000002",
        "event_ts": "1358878755.000002",
    }
    with caplog.at_level(logging.DEBUG):
        await slack.handle_message(event, None)
    assert "Ignoring `message_deleted` event" in caplog.text


@pytest.mark.asyncio
async def test_handle_message__subtype_changed(caplog):
    event = {
        "type": "message",
        "subtype": "message_changed",
        "hidden": True,
        "channel": "C123ABC456",
        "ts": "1358878755.000001",
        "message": {
            "type": "message",
            "user": "U123ABC456",
            "text": "Hello, world!",
            "ts": "1355517523.000005",
            "edited": {"user": "U123ABC456", "ts": "1358878755.000001"},
        },
    }
    with caplog.at_level(logging.DEBUG):
        await slack.handle_message(event, None)
    assert "Ignoring `message_changed` event" in caplog.text


@pytest.mark.asyncio
async def test_send_response(monkeypatch):
    urlopen = mock.AsyncMock()
    urlopen.__enter__().read.return_value = b"Hello"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: urlopen)
    execute_run = mock.AsyncMock(return_value="Hello World!")
    monkeypatch.setattr(bot, "execute_run", execute_run)
    tts = mock.AsyncMock(return_value=b"Hello")
    monkeypatch.setattr(bot, "tts", tts)
    get_bot_user_id = mock.AsyncMock(return_value="bot-1")
    monkeypatch.setattr(slack, "get_bot_user_id", get_bot_user_id)
    monkeypatch.setattr(
        "sam.bot.get_thread",
        mock.AsyncMock(return_value={"model": "gpt-4o-mini", "messages": []}),
    )
    say = mock.AsyncMock()
    event = {
        "channel": "channel-1",
        "client_msg_id": "client-msg-1",
        "channel_type": "im",
        "user": "user-1",
        "ts": 12321345,
        "text": "Hello",
        "files": [
            {
                "url_private": "https://example.com/file.mp3",
                "name": "file.mp3",
            }
        ],
    }
    await slack.send_response(event, say, voice_response=True)

    assert execute_run.called
    assert execute_run.call_args == mock.call(
        thread_id="channel-1",
    )
    assert tts.called
    assert tts.call_args == mock.call("Hello World!")


@pytest.mark.asyncio
async def test_send_response__thread(monkeypatch):
    urlopen = mock.AsyncMock()
    urlopen.__enter__().read.return_value = b"Hello"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: urlopen)
    execute_run = mock.AsyncMock(return_value="Hello World!")
    monkeypatch.setattr(bot, "execute_run", execute_run)
    tts = mock.AsyncMock(return_value=b"Hello")
    monkeypatch.setattr(bot, "tts", tts)
    get_bot_user_id = mock.AsyncMock(return_value="bot-1")
    monkeypatch.setattr(slack, "get_bot_user_id", get_bot_user_id)
    monkeypatch.setattr(
        "sam.bot.get_thread",
        mock.AsyncMock(return_value={"model": "gpt-4o-mini", "messages": []}),
    )
    say = mock.AsyncMock()
    event = {
        "channel": "channel-1",
        "client_msg_id": "client-msg-1",
        "channel_type": "im",
        "user": "user-1",
        "thread_ts": 12321345,
        "text": "Hello",
        "files": [
            {
                "url_private": "https://audio-samples.github.io/samples/mp3/blizzard_tts_unbiased/sample-0/real.mp3",
                "name": "file.mp3",
            }
        ],
    }
    await slack.send_response(event, say, voice_response=True)

    assert execute_run.called
    assert execute_run.call_args == mock.call(
        thread_id="channel-1",
    )
    assert tts.called
    assert tts.call_args == mock.call("Hello World!")


def test_markdown2mrkdwn():
    assert slack.markdown2mrkdwn("Hello **World**!") == "Hello *World*!", "Bold"
    assert slack.markdown2mrkdwn("Hello *World*!") == "Hello _World_!", "Italic"
    assert slack.markdown2mrkdwn("Hello ~~World~~!") == "Hello ~World~!", (
        "Strikethrough"
    )
    assert (
        slack.markdown2mrkdwn("Hello [World](https://example.com)!")
        == "Hello <https://example.com|World>!"
    ), "Link"
    assert (
        slack.markdown2mrkdwn("Hello [World\n](https://example.com)!")
        == "Hello <https://example.com|World\n>!"
    ), "Link"
    assert (
        slack.markdown2mrkdwn("# Heading 1\n\n## Heading 2")
        == "*Heading 1*\n\n*Heading 2*"
    ), "Heading"

import logging
from unittest import mock

import pytest

from sam import bot, slack


@pytest.mark.asyncio
async def test_get_bot_user_id(monkeypatch):
    auth_test = mock.AsyncMock(return_value={"user_id": "bot-1"})
    monkeypatch.setattr(slack.AsyncWebClient, "auth_test", auth_test)
    assert await slack.get_bot_user_id() == "bot-1"
    assert auth_test.called


@pytest.mark.asyncio
async def test_handle_message(monkeypatch):
    urlopen = mock.AsyncMock()
    urlopen.__enter__().read.return_value = b"Hello"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: urlopen)
    add_message = mock.AsyncMock(return_value=(["file-1"], False))
    monkeypatch.setattr(bot, "add_message", add_message)
    send_response = mock.AsyncMock()
    monkeypatch.setattr(slack, "send_response", send_response)
    get_bot_user_id = mock.AsyncMock(return_value="bot-1")
    monkeypatch.setattr(slack, "get_bot_user_id", get_bot_user_id)
    monkeypatch.setattr(
        "sam.utils.get_thread_id", mock.AsyncMock(return_value="thread-1")
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
                "url_private": "https://audio-samples.github.io/samples/mp3/blizzard_tts_unbiased/sample-0/real.mp3",
                "name": "file.mp3",
            }
        ],
    }
    await slack.handle_message(event, say)
    assert add_message.called
    assert add_message.call_args == mock.call(
        thread_id="thread-1", content="Hello", files=[("file.mp3", b"Hello")]
    )
    assert urlopen.__enter__().read.called
    assert send_response.called
    assert send_response.call_args == mock.call(
        {
            "channel": "channel-1",
            "client_msg_id": "client-msg-1",
            "channel_type": "im",
            "user": "user-1",
            "text": "Hello",
            "files": [
                {
                    "url_private": "https://audio-samples.github.io/samples/mp3/blizzard_tts_unbiased/sample-0/real.mp3",
                    "name": "file.mp3",
                }
            ],
        },
        say,
        file_ids=["file-1"],
        voice_prompt=False,
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
    assert "Ignoring message_deleted event" in caplog.text


def test_get_user_profile(monkeypatch):
    client = mock.MagicMock()
    client.users_profile_get.return_value = {
        "profile": {
            "display_name": "Spidy",
            "status_text": "With great power comes great responsibility",
            "pronouns": "spider/superhero",
            "email": "peter.parker@avengers.com",
        }
    }
    monkeypatch.setattr(slack.WebClient, "users_profile_get", client.users_profile_get)
    assert slack.get_user_profile("user-1") == {
        "display_name": "Spidy",
        "status_text": "With great power comes great responsibility",
        "pronouns": "spider/superhero",
        "email": "peter.parker@avengers.com",
    }


def test_get_user_specific_instructions(monkeypatch):
    client = mock.MagicMock()
    client.users_profile_get.return_value = {
        "profile": {
            "display_name": "Spidy",
            "status_text": "With great power comes great responsibility",
            "pronouns": "spider/superhero",
            "email": "peter.parker@avengers.com",
        }
    }
    monkeypatch.setattr(slack.WebClient, "users_profile_get", client.users_profile_get)
    instructions = slack.get_user_specific_instructions("user-1")
    assert "You MUST ALWAYS address the user as <@user-1>." in instructions
    assert "You may refer to the user as Spidy." in instructions
    assert "The user's email is peter.parker@avengers.com." in instructions
    assert "The user's pronouns are spider/superhero." in instructions


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
        slack,
        "get_user_specific_instructions",
        lambda *args, **kwargs: "user_instructions",
    )
    monkeypatch.setattr(
        slack, "get_user_profile", lambda *args, **kwargs: {"name": "Sam"}
    )
    monkeypatch.setattr(
        "sam.utils.get_thread_id", mock.AsyncMock(return_value="thread-1")
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
    await slack.send_response(event, say, voice_prompt=True)

    assert execute_run.called
    assert execute_run.call_args == mock.call(
        thread_id="thread-1",
        assistant_id=None,
        additional_instructions="user_instructions",
        file_ids=None,
        name="Sam",
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
        slack,
        "get_user_specific_instructions",
        lambda *args, **kwargs: "user_instructions",
    )
    monkeypatch.setattr(
        slack, "get_user_profile", lambda *args, **kwargs: {"name": "Sam"}
    )
    monkeypatch.setattr(
        "sam.utils.get_thread_id", mock.AsyncMock(return_value="thread-1")
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
    await slack.send_response(event, say, voice_prompt=True)

    assert execute_run.called
    assert execute_run.call_args == mock.call(
        thread_id="thread-1",
        assistant_id=None,
        additional_instructions="user_instructions",
        file_ids=None,
        name="Sam",
    )
    assert tts.called
    assert tts.call_args == mock.call("Hello World!")

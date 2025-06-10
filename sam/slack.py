from __future__ import annotations

import functools
import io
import json
import logging
import random
import re
from typing import Any

import httpx
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncSay
from slack_sdk import errors
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from . import bot, config, redis_utils

logger = logging.getLogger(__name__)

_USER_HANDLE = None

ACKNOWLEDGMENT_SMILEYS = [
    "thumbsup",
    "ok_hand",
    "eyes",
    "wave",
    "robot_face",
    "saluting_face",
    "v",
    "100",
    "muscle",
    "thought_balloon",
    "speech_balloon",
    "space_invader",
    "call_me_hand",
]


async def get_bot_user_id():
    """Get the Slack bot's user id."""
    client = AsyncWebClient(token=config.SLACK_BOT_TOKEN)
    global _USER_HANDLE
    if _USER_HANDLE is None:
        logger.debug("Fetching the bot's user id")
        response = await client.auth_test()
        _USER_HANDLE = response["user_id"]
        logger.debug("Bot's user id is %s", _USER_HANDLE)
    return _USER_HANDLE


async def handle_message(event: {str, Any}, say: AsyncSay):
    """Handle a message event from Slack."""
    if event.get("subtype") in ["message_changed", "message_deleted"]:
        logger.debug("Ignoring `%s` event", event["subtype"])
        return
    bot_id = await get_bot_user_id()
    channel_id = event["channel"]
    channel_type = event["channel_type"]
    text = event["text"]
    text = text.replace(f"<@{bot_id}>", "Sam")
    # We may only add messages to a thread while the assistant is not running
    files = []
    for file in event.get("files", []):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                file["url_private"],
                headers={"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
            )
        response.raise_for_status()
        files.append((file["name"], io.BytesIO(response.content)))

    async with (
        redis_utils.async_redis_client(config.REDIS_URL) as redis_client,
        redis_client.lock(channel_id, timeout=10 * 60, thread_local=False),
    ):  # 10 minutes
        has_attachments, has_audio = await bot.add_message(
            thread_id=channel_id,
            content=text,
            files=files,
        )

    # we need to release the lock before starting a new run
    if (
        channel_type == "im"
        or event.get("parent_user_id") == bot_id
        or random.random() < config.RANDOM_RUN_RATIO  # noqa: S311
    ):
        await send_response(event, say, voice_response=has_audio)


@functools.lru_cache(maxsize=128)
def get_user_profile(user_id: str) -> dict[str, Any]:
    """Get the profile of a user."""
    client = WebClient(token=config.SLACK_BOT_TOKEN)
    return client.users_profile_get(user=user_id)["profile"]


async def send_response(
    event: {str, Any},
    say: AsyncSay,
    voice_response: bool = False,
):
    """Send a response to a message event from Slack."""
    logger.debug("process_run=%s", json.dumps(event))
    channel_id = event["channel"]
    user_id = event["user"]
    try:
        timestamp = event["ts"]
    except KeyError:
        timestamp = event["thread_ts"]

    # We may wait for the messages being processed, before starting a new run
    async with (
        redis_utils.async_redis_client(config.REDIS_URL) as redis_client,
        redis_client.lock(channel_id, timeout=10 * 60),
    ):  # 10 minutes
        logger.info("User=%s starting run for Thread=%s", user_id, channel_id)
        await say.client.reactions_add(
            channel=channel_id,
            name=random.choice(ACKNOWLEDGMENT_SMILEYS),  # noqa: S311
            timestamp=timestamp,
        )
        text_response = await bot.execute_run(
            thread_id=channel_id,
        )

        msg = await say(
            channel=say.channel,
            text=markdown2mrkdwn(text_response),
            mrkdwn=True,
            thread_ts=event.get("thread_ts", None),
        )
        logger.info(
            "Sam responded to the User=%s in Channel=%s via Text",
            user_id,
            channel_id,
        )

        if voice_response:
            await say.client.files_upload_v2(
                filename="response.mp3",
                title="Voice Response",
                content=await bot.tts(text_response),
                channel=say.channel,
                thread_ts=event.get("thread_ts", None),
                ts=msg["ts"],
            )
            logger.info(
                "Sam responded to the User=%s in Channel=%s via Voice",
                user_id,
                channel_id,
            )


def get_app():  # pragma: no cover
    from slack_bolt.async_app import AsyncApp

    app = AsyncApp(token=config.SLACK_BOT_TOKEN)
    app.event("message")(handle_message)
    app.event("app_mention")(send_response)
    return app


async def run_slack():
    handler = AsyncSocketModeHandler(get_app(), config.SLACK_APP_TOKEN)
    await handler.start_async()


def fetch_coworker_contacts(_context=None) -> str:
    """Fetch profile data about your coworkers from Slack.

    The profiles include:
    - first a last name
    - email address
    - status
    - pronouns
    """
    client = WebClient(token=config.SLACK_BOT_TOKEN)
    try:
        response = client.users_list()
    except errors.SlackClientError:
        logger.exception("Failed to fetch coworkers' profiles")
        return "failed to fetch coworkers' profiles"
    else:
        logger.debug("Fetched coworkers' profiles: %r", response["members"])

        profiles = {}
        for member in response["members"]:
            profile = member.get("profile", {})
            if not any(
                [
                    member["deleted"],
                    member["is_bot"],
                    member["is_app_user"],
                    "real_name" not in profile,
                ]
            ):
                profiles[profile["real_name"]] = {
                    "first_name": profile.get("first_name"),
                    "last_name": profile.get("last_name"),
                    "email": profile.get("email"),
                    "status": profile.get("status_text"),
                    "pronouns": profile.get("pronouns"),
                }
        return json.dumps(profiles)


MD_MRKDWN_PATTERN = [
    (re.compile(r"[*_]([^*_]*?)[*_]"), r"_\1_"),  # italic
    (re.compile(r"~{2}(.*?)~{2}"), r"~\1~"),  # strikethrough
    (re.compile(r"[*_]{2}([^*_]*?)[*_]{2}"), r"*\1*"),  # bold
    (re.compile(r"\[(.*?)]\((.*?)\)", re.DOTALL), r"<\2|\1>"),  # link
    (re.compile(r"^#{1,6}\s+(.*?)$", re.MULTILINE), r"*\1*"),  # heading
]


def markdown2mrkdwn(text: str) -> str:
    """Convert Markdown to Slack's mrkdwn format."""
    for pattern, replacement in MD_MRKDWN_PATTERN:
        text = pattern.sub(replacement, text)
    return text

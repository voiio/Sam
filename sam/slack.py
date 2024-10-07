from __future__ import annotations

import functools
import json
import logging
import random
import re
import traceback
import urllib.request
from datetime import datetime
from typing import Any

from slack_bolt.async_app import AsyncSay
from slack_sdk import errors
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

import sam.bot

from . import bot, config
from .utils import async_redis_client

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
    thread_id = await sam.bot.get_thread_id(channel_id)
    # We may only add messages to a thread while the assistant is not running
    files = []
    for file in event.get("files", []):
        req = urllib.request.Request(  # noqa: S310
            file["url_private"],
            headers={"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
        )
        with urllib.request.urlopen(req) as response:  # noqa: S310
            files.append((file["name"], response.read()))

    async with (
        async_redis_client(config.REDIS_URL, config.REDIS_VERIFY_SSL) as redis_client,
        redis_client.lock(thread_id, timeout=10 * 60, thread_local=False),
    ):  # 10 minutes
        try:
            has_attachments, has_audio = await bot.add_message(
                thread_id=thread_id,
                content=text,
                files=files,
            )
        except OSError:
            logger.warning(
                "Failed to add message to thread_id=%s", thread_id, exc_info=True
            )
            # Only relevant for direct messages
            if channel_type == "im" or event.get("parent_user_id") == bot_id:
                has_attachments, has_audio = await bot.add_message(
                    thread_id=thread_id,
                    content=f"Briefly inform the user about: {traceback.format_exc(limit=1)} Include links.",
                )

    # we need to release the lock before starting a new run
    if (
        channel_type == "im"
        or event.get("parent_user_id") == bot_id
        or random.random() < config.RANDOM_RUN_RATIO  # noqa: S311
    ):
        await send_response(
            event, say, file_search=has_attachments, voice_response=has_audio
        )


@functools.lru_cache(maxsize=128)
def get_user_profile(user_id: str) -> dict[str, Any]:
    """Get the profile of a user."""
    client = WebClient(token=config.SLACK_BOT_TOKEN)
    return client.users_profile_get(user=user_id)["profile"]


@functools.lru_cache(maxsize=128)
def get_user_specific_instructions(user_id: str) -> str:
    """Get the user-specific instructions."""
    profile = get_user_profile(user_id)
    name = profile["display_name"]
    email = profile["email"]
    pronouns = profile.get("pronouns")
    local_time = datetime.now(tz=config.TIMEZONE)
    instructions = [
        f"You MUST ALWAYS address the user as <@{user_id}>.",
        f"You may refer to the user as {name}.",
        f"The user's email is {email}.",
        f"The time is {local_time.isoformat()}.",
    ]
    if pronouns:
        instructions.append(f"The user's pronouns are {pronouns}.")
    return "\n".join(instructions)


async def send_response(
    event: {str, Any},
    say: AsyncSay,
    file_search: bool = False,
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
    thread_id = await sam.bot.get_thread_id(channel_id)

    # We may wait for the messages being processed, before starting a new run
    async with (
        async_redis_client(config.REDIS_URL, config.REDIS_VERIFY_SSL) as redis_client,
        redis_client.lock(thread_id, timeout=10 * 60),
    ):  # 10 minutes
        logger.info("User=%s starting run for Thread=%s", user_id, thread_id)
        await say.client.reactions_add(
            channel=channel_id,
            name=random.choice(ACKNOWLEDGMENT_SMILEYS),  # noqa: S311
            timestamp=timestamp,
        )
        text_response = await bot.execute_run(
            thread_id=thread_id,
            assistant_id=config.OPENAI_ASSISTANT_ID,
            additional_instructions=get_user_specific_instructions(user_id),
            file_search=file_search,
            **get_user_profile(user_id),
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


def fetch_coworker_contacts(_context=None) -> str:
    """Fetch profile data about your coworkers from Slack.

    The profiles include:
    - first & last name
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
    """Convert markdown to Slack's mrkdwn format."""
    for pattern, replacement in MD_MRKDWN_PATTERN:
        text = pattern.sub(replacement, text)
    return text

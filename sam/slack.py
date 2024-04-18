import asyncio
import enum
import json
import logging
import random  # nosec
import urllib.request
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from openai import AsyncOpenAI
from slack_bolt.async_app import AsyncApp, AsyncSay

from . import bot, config, utils

logger = logging.getLogger("sam")

client = AsyncOpenAI()
app = AsyncApp(token=config.SLACK_BOT_TOKEN)

USER_HANDLE = None

AUDIO_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]


async def handle_message(event: {str, Any}, say: AsyncSay):
    logger.debug(f"handle_message={json.dumps(event)}")
    global USER_HANDLE
    if USER_HANDLE is None:
        logger.debug("Fetching the bot's user id")
        response = await say.client.auth_test()
        USER_HANDLE = response["user_id"]
        logger.debug(f"Bot's user id is {USER_HANDLE}")
    channel_id = event["channel"]
    client_msg_id = event["client_msg_id"]
    channel_type = event["channel_type"]
    user_id = event["user"]
    text = event["text"]
    text = text.replace(f"<@{USER_HANDLE}>", "Sam")
    thread_id = await utils.get_thread_id(channel_id)
    # We may only add messages to a thread while the assistant is not running
    async with (
        redis.from_url(config.REDIS_URL) as redis_client,
        redis_client.lock(thread_id, timeout=10 * 60, thread_local=False),
    ):  # 10 minutes
        file_ids = []
        voice_prompt = False
        if "files" in event:
            for file in event["files"]:
                req = urllib.request.Request(
                    file["url_private"],
                    headers={"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
                )
                with urllib.request.urlopen(req) as response:  # nosec
                    if file["filetype"] in AUDIO_FORMATS:
                        text += "\n" + await client.audio.transcriptions.create(
                            model="whisper-1",
                            file=(file["name"], response.read()),
                            response_format="text",
                        )
                        logger.info(f"User={user_id} added Audio={file['id']}")
                        voice_prompt = True
                    else:
                        new_file = await client.files.create(
                            file=(file["name"], response.read()),
                            purpose="assistants",
                        )
                        file_ids.append(new_file.id)
                        logger.info(
                            f"User={user_id} added File={file_ids[-1]} to Thread={thread_id}"
                        )
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            content=text,
            role="user",
        )
        logger.info(
            f"User={user_id} added Message={client_msg_id} added to Thread={thread_id}"
        )
        if (
            channel_type == "im"
            or event.get("parent_user_id") == USER_HANDLE
            or random.random() < config.RANDOM_RUN_RATIO  # nosec
        ):
            # we need to run the assistant in a separate thread, otherwise we will
            # block the main thread:
            # process_run(event, say, voice_prompt=voice_prompt)
            asyncio.create_task(process_run(event, say, voice_prompt=voice_prompt))


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


async def process_run(event: {str, Any}, say: AsyncSay, voice_prompt: bool = False):
    logger.debug(f"process_run={json.dumps(event)}")
    channel_id = event["channel"]
    user_id = event["user"]
    profile = (await say.client.users_profile_get(user=user_id))["profile"]
    name = profile["display_name"]
    email = profile["email"]
    pronouns = profile.get("pronouns")
    local_time = datetime.now().astimezone(config.TIMEZONE).strftime("%H:%M")
    additional_instructions = (
        f"You MUST ALWAYS address the user as <@{user_id}>.\n"
        f"You may refer to the user as {name}.\n"
        f"The user's email is {email}.\n"
        f"The time is {local_time}.\n"
    )
    if pronouns:
        additional_instructions += f"The user's pronouns are {pronouns}.\n"
    try:
        ts = event["ts"]
    except KeyError:
        ts = event["thread_ts"]
    thread_id = await utils.get_thread_id(channel_id)
    # We may wait for the messages being processed, before starting a new run
    async with (
        redis.from_url(config.REDIS_URL) as redis_client,
        redis_client.lock(thread_id, timeout=10 * 60),
    ):  # 10 minutes
        logger.info(f"User={user_id} starting run for Thread={thread_id}")
        await say.client.reactions_add(
            channel=channel_id,
            name=random.choice(ACKNOWLEDGMENT_SMILEYS),  # nosec
            timestamp=ts,
        )
        message_content = await bot.run(
            thread_id=thread_id,
            assistant_id=config.OPENAI_ASSISTANT_ID,
            additional_instructions=additional_instructions,
            **profile,
        )

        msg = await say(
            channel=say.channel,
            text=message_content.value,
            mrkdwn=True,
            thread_ts=event.get("thread_ts", None),
        )

        if voice_prompt:
            response = await client.audio.speech.create(
                model="tts-1-hd",
                voice="alloy",
                input=message_content.value,
            )
            await say.client.files_upload_v2(
                content=response.read(),
                channels=say.channel,
                thread_ts=event.get("thread_ts", None),
                ts=msg["ts"],
            )
            logger.info(
                f"Sam responded to the User={user_id} in Channel={channel_id} via Voice"
            )

        logger.info(
            f"Sam responded to the User={user_id} in Channel={channel_id} via Text"
        )


app.event("message")(handle_message)
app.event("app_mention")(process_run)

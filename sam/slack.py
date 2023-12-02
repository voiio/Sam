import json
import logging
import time
from typing import Any

from openai import OpenAI
from slack_bolt import App, Say

from . import config, utils

logger = logging.getLogger("sam")

client = OpenAI()
app = App(token=config.SLACK_BOT_TOKEN)

USER_HANDLE = None


def handle_message(event: {str, Any}, say: Say):
    logger.debug(f"handle_message={json.dumps(event)}")
    global USER_HANDLE
    if USER_HANDLE is None:
        logger.debug("Fetching the bot's user id")
        response = say.client.auth_test()
        USER_HANDLE = response["user_id"]
    channel_id = event["channel"]
    client_msg_id = event["client_msg_id"]
    channel_type = event["channel_type"]
    user_id = event["user"]
    text = event["text"]
    text = text.replace(f"<@{USER_HANDLE}>", "Sam")
    thread_id = utils.get_thread_id(channel_id)
    client.beta.threads.messages.create(thread_id=thread_id, content=text, role="user")
    logger.info(
        f"User={user_id} added Message={client_msg_id} added to Thread={thread_id}"
    )
    if channel_type == "im":
        process_run(event, say)


def process_run(event: {str, Any}, say: Say):
    logger.debug(f"process_run={json.dumps(event)}")
    channel_id = event["channel"]
    user_id = event["user"]
    thread_id = utils.get_thread_id(channel_id)
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=config.OPENAI_ASSISTANT_ID,
    )
    msg = say(f":speech_balloon:", mrkdwn=True)
    logger.info(f"User={user_id} started Run={run.id} for Thread={thread_id}")
    cycle = 0
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        time.sleep(2**cycle)
    if run.status != "completed":
        logger.error(run.last_error)
        say(
            f"🤖 {run.last_error.message}",
        )
        logger.error(f"Run {run.id} {run.status} for Thread {thread_id}")
        logger.error(run.last_error.message)
        return
    logger.info(f"Run={run.id} {run.status} for Thread={thread_id}")

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages:
        if message.role == "assistant":
            say.client.chat_update(
                channel=say.channel,
                ts=msg["ts"],
                text=message.content[0].text.value,
                mrkdwn=True,
            )
            logger.info(f"Sam responded to the User={user_id} in Channel={channel_id}")
            break


app.event("message")(handle_message)
app.event("app_mention")(process_run)

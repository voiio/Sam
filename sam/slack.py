import logging
import re
import time
from typing import Any

from openai import OpenAI
from slack_bolt import App, Say

logger = logging.getLogger("sam")

client = OpenAI()

from . import config, utils

# Event API & Web API
app = App(token=config.SLACK_BOT_TOKEN)


USER_HANDLE = re.compile(r"<@([A-Z0-9]+)>", flags=re.IGNORECASE)


def handle_message_events(event: {str, Any}, say: Say):
    channel_id = event["channel"]
    logger.info(
        f"type={event['type']} client_msg_id={event['client_msg_id']} channel={channel_id} user={event['user']}"
    )
    text = event["text"]
    text = USER_HANDLE.sub(r"Sam", text)
    thread_id = utils.get_thread_id(channel_id)
    client.beta.threads.messages.create(thread_id=thread_id, content=text, role="user")
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=config.OPENAI_ASSISTANT_ID,
    )
    cycle = 0
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        time.sleep(2**cycle)
    if run.status != "completed":
        logger.error(run.last_error)
        say(f"🤖 {run.last_error.message}")

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages:
        if message.role == "assistant":
            say(message.content[0].text.value, mrkdwn=True)
            break


app.event("message")(handle_message_events)
app.event("app_mention")(handle_message_events)

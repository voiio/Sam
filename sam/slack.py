import logging
import time
from typing import Any

from openai import OpenAI
from slack_bolt import App, Say

logger = logging.getLogger(__name__)

client = OpenAI()

from . import config, utils

# Event API & Web API
app = App(token=config.SLACK_BOT_TOKEN)


def handle_message_events(event: {str, Any}, say: Say):
    user_id = event["user"]
    text = event["text"]
    thread_id = utils.get_thread_id(f"@{user_id}")
    client.beta.threads.messages.create(thread_id=thread_id, content=text, role="user")
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=config.OPENAI_ASSISTANT_ID,
        instructions=f"Please address the user as <@{user_id}>. The user is your colleague.",
    )
    say(f"Sure, I'm on it!")
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
            say(f"👩‍💻 {message.content[0].text.value}")


app.event("message")(handle_message_events)
app.event("app_mentions")(handle_message_events)

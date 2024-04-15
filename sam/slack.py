import json
import logging
import random  # nosec
import threading
import time
import urllib.request
from typing import Any

from openai import OpenAI
from slack_bolt import App, Say

from . import config, utils

logger = logging.getLogger("sam")

client = OpenAI()
app = App(token=config.SLACK_BOT_TOKEN)

USER_HANDLE = None

AUDIO_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]


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
    # We may only add messages to a thread while the assistant is not running
    with utils.storage.lock(
        thread_id, timeout=10 * 60, thread_local=False
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
                        text += "\n" + client.audio.transcriptions.create(
                            model="whisper-1",
                            file=(file["name"], response.read()),
                            response_format="text",
                        )
                        logger.info(f"User={user_id} added Audio={file['id']}")
                        voice_prompt = True
                    else:
                        file_ids.append(
                            client.files.create(
                                file=(file["name"], response.read()),
                                purpose="assistants",
                            ).id
                        )
                        logger.info(
                            f"User={user_id} added File={file_ids[-1]} to Thread={thread_id}"
                        )
        client.beta.threads.messages.create(
            thread_id=thread_id,
            content=text,
            role="user",
            file_ids=file_ids,
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
            threading.Thread(
                target=process_run,
                args=(event, say),
                kwargs={"voice_prompt": voice_prompt},
            ).start()


ACKNOWLEDGMENT_SMILEYS = [
    "thumbsup",
    "ok_hand",
    "eyes",
    "wave",
    "robot_face",
    "salute_face",
    "v",
    "yawning_face",
    "100",
    "muscle",
    "thought_balloon",
    "speech_balloon",
    "space_invader",
    "call_me_hand",
]


def process_run(event: {str, Any}, say: Say, voice_prompt: bool = False):
    logger.debug(f"process_run={json.dumps(event)}")
    channel_id = event["channel"]
    user_id = event["user"]
    try:
        ts = event["ts"]
    except KeyError:
        ts = event["thread_ts"]
    thread_id = utils.get_thread_id(channel_id)
    # We may wait for the messages being processed, before starting a new run
    with utils.storage.lock(thread_id, timeout=10 * 60):  # 10 minutes
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=config.OPENAI_ASSISTANT_ID,
            tools=[
                utils.func_to_tool(utils.send_email),
                utils.func_to_tool(utils.web_search),
                utils.func_to_tool(utils.fetch_website),
            ],
        )
        say.client.reactions_add(
            channel=channel_id,
            name=random.choice(ACKNOWLEDGMENT_SMILEYS),  # nosec
            timestamp=ts,
        )
        logger.info(f"User={user_id} started Run={run.id} for Thread={thread_id}")
        for i in range(14):  # ~ 5 minutes
            if run.status not in ["queued", "in_progress", "requires_action"]:
                break
            if (
                run.required_action
                and run.required_action.submit_tool_outputs
                and run.required_action.submit_tool_outputs.tool_calls
            ):
                tool_outputs = []

                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    logger.info(
                        f"Tool Call={tool_call.id} Function={tool_call.function.name}"
                    )
                    logger.debug(
                        f"Tool Call={tool_call.id} Arguments={tool_call.function.arguments}"
                    )
                    fn = getattr(utils, tool_call.function.name)
                    kwargs = json.loads(tool_call.function.arguments)
                    tool_outputs.append(
                        {
                            "tool_call_id": tool_call.id,  # noqa
                            "output": fn(**kwargs),
                        }
                    )

                client.beta.threads.runs.submit_tool_outputs(
                    run.id,  # noqa
                    thread_id=thread_id,
                    tool_outputs=tool_outputs,
                )
            time.sleep(min(2**i, 30))  # exponential backoff capped at 30 seconds
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run.status == "failed":
            logger.error(run.last_error)
            say(
                channel=say.channel,
                text="🤖 {run.last_error.message}",
            )
            logger.error(f"Run {run.id} {run.status} for Thread {thread_id}")
            logger.error(run.last_error.message)
            return
        elif run.status != "completed":
            logger.error(f"Run={run.id} {run.status} for Thread {thread_id}")
            say(
                channel=say.channel,
                text="🤯",
            )
            return
        logger.info(f"Run={run.id} {run.status} for Thread={thread_id}")

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for message in messages:
            if message.role == "assistant":
                message_content = message.content[0].text

                annotations = message_content.annotations
                citations = []

                # Iterate over the annotations and add footnotes
                for index, annotation in enumerate(annotations):
                    message_content.value = message_content.value.replace(
                        annotation.text, f" [{index}]"
                    )

                    if file_citation := getattr(annotation, "file_citation", None):
                        cited_file = client.files.retrieve(file_citation.file_id)
                        citations.append(
                            f"[{index}] {file_citation.quote} — {cited_file.filename}"
                        )
                    elif file_path := getattr(annotation, "file_path", None):
                        cited_file = client.files.retrieve(file_path.file_id)
                        citations.append(f"[{index}]({cited_file.filename})")

                # Add footnotes to the end of the message before displaying to user
                message_content.value += "\n" + "\n".join(citations)

                try:
                    msg = say(
                        channel=say.channel,
                        text=message_content.value,
                        mrkdwn=True,
                    )
                except ValueError as e:
                    logger.exception("Failed to send message")
                    say(
                        channel=say.channel,
                        text="🤯",
                    )
                    return

                if voice_prompt:
                    response = client.audio.speech.create(
                        model="tts-1-hd",
                        voice="alloy",
                        input=message_content.value,
                    )
                    say.client.files_upload(
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
                break


app.event("message")(handle_message)
app.event("app_mention")(process_run)

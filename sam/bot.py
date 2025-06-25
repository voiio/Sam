from __future__ import annotations

import datetime
import io
import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
import openai
from openai._types import FileTypes

from . import config, redis_utils

AUDIO_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

logger = logging.getLogger(__name__)


async def execute_run(
    thread_id: str,
) -> str:
    """Run the assistant on the OpenAI thread."""
    logger.info(
        "Running in thread %s with additional instructions",
        thread_id,
    )
    thread = await get_thread(thread_id)
    try:
        thread = await chat_with_model(thread)
    except (httpx.HTTPStatusError, httpx.RequestError):
        logger.exception("Run %s failed", thread_id)
        return "🤯"
    else:
        await set_thread(thread_id, thread)
        return thread["messages"][-1]["content"]


async def add_message(
    thread_id: str,
    content: str,
    files: list[tuple[str, io.BytesIO]] = None,
) -> tuple[bool, bool]:
    """Add a message to the thread."""
    logger.info("Adding message to thread %s", thread_id)
    file_ids = []
    voice_prompt = False
    for file_name, file_content in files or []:
        if Path(file_name).suffix.lstrip(".") in AUDIO_FORMATS:
            logger.debug("Transcribing audio file %s", file_name)
            content += "\n" + await stt((file_name, file_content))
            voice_prompt = True
        else:
            logger.debug("Uploading file %s", file_name)
            headers = {
                "Authorization": f"Bearer {config.OPEN_WEBUI_API_KEY}",
                "Accept": "application/json",
            }
            files = {"file": file_content}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    urljoin(config.OPEN_WEBUI_URL, "/api/v1/files/"),
                    headers=headers,
                    files=files,
                )
            response.raise_for_status()
            new_file = response.json()
            file_ids.append(new_file["id"])

    thread = await get_thread(thread_id)
    thread["files"] += [{"type": "file", "id": file_id} for file_id in file_ids]
    thread["messages"].append({"role": "user", "content": content})
    await set_thread(thread_id, thread)

    return bool(file_ids), voice_prompt


async def tts(text: str) -> bytes:
    """Convert text to speech using the OpenAI API."""
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    response = await client.audio.speech.create(
        model=config.TTS_MODEL,
        voice=config.TTS_VOICE,
        input=text,
    )
    return response.read()


async def stt(audio: FileTypes) -> str:
    """Convert speech to text using the OpenAI API."""
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio,
        prompt=config.STT_PROMPT,
    )
    return response.text


async def get_thread(slack_id: str) -> dict[str, list[dict[str, str | list[dict]]]]:
    """Get the thread from the user_id or channel.

    Args:
        slack_id: The user or channel id.

    Returns:
        The thread id.
    """
    async with redis_utils.async_redis_client(config.REDIS_URL) as redis_client:
        thread = json.loads((await redis_client.get(f"thread_{slack_id}")) or "{}")
        if not thread:
            thread = {
                "messages": [],
                "files": [],
            }
        return thread | {
            "model": config.OPEN_WEBUI_MODEL,
            "features": {
                "image_generation": False,
                "code_interpreter": False,
                "web_search": False,
                "memory": False,
            },
            "tool_ids": await get_tool_ids(),
        }


async def set_thread(
    slack_id: str, thread: dict[str, list[dict[str, str | list[dict]]]]
):
    """Set the thread for the user or channel.

    Args:
        slack_id: The user or channel id.
        thread: The thread to set, as a list of message dictionaries.
    """
    # midnight
    if config.GROUNDHOG_DAY_MODE:
        now = datetime.datetime.now()
        midnight = datetime.datetime.combine(
            now.date() + datetime.timedelta(days=1), datetime.time.min
        )
        exat = int(time.mktime(midnight.timetuple()))
    else:
        exat = None

    async with redis_utils.async_redis_client(config.REDIS_URL) as redis_client:
        await redis_client.set(f"thread_{slack_id}", json.dumps(thread), exat=exat)


OPEN_WEBUI_AUTH_HEADERS = {
    "Authorization": f"Bearer {config.OPEN_WEBUI_API_KEY}",
    "Content-Type": "application/json",
}


async def get_tool_ids() -> list[str]:
    """Get the default tools configured for an agent."""
    url = urljoin(config.OPEN_WEBUI_URL, "/api/models")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=OPEN_WEBUI_AUTH_HEADERS, timeout=5)
    for model in response.json()["data"]:
        if model["id"] == config.OPEN_WEBUI_MODEL:
            return model["info"]["meta"]["toolIds"]
    return []


async def chat_with_model(thread: dict[str, list[dict[str, str | list[dict]]]]):
    url = urljoin(config.OPEN_WEBUI_URL, "/api/chat/completions")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, json=thread, timeout=60 * 10, headers=OPEN_WEBUI_AUTH_HEADERS
        )
    response.raise_for_status()
    data = response.json()
    if "choices" in data and data["choices"]:
        thread["messages"].append(data["choices"][0]["message"])
    return thread

from __future__ import annotations

import asyncio
import enum
import inspect
import logging
import random

import openai
import redis.asyncio as redis
import yaml

from . import config

logger = logging.getLogger(__name__)

__all__ = ["get_thread_id", "func_to_tool"]


type_map = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "list": "array",
    "dict": "object",
    str: "string",
    int: "integer",
    float: "number",
    list: "array",
    dict: "object",
    enum.StrEnum: "string",
    enum.IntEnum: "integer",
}


def func_to_tool(fn: callable) -> dict:
    """
    Convert a function to an OpenAI tool definition based on signature and docstring.

    The docstring should be formatted using the Google Napolean style.
    """
    signature: inspect.Signature = inspect.signature(fn)
    if signature.parameters:
        description, args = fn.__doc__.split("Args:")
        doc_data = yaml.safe_load(args.split("Returns:")[0])
    else:
        description = fn.__doc__
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": "\n".join(
                filter(None, (line.strip() for line in description.splitlines()))
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": type_map[param.annotation],
                        "description": doc_data[param.name],
                    }
                    for param in signature.parameters.values()
                },
                "required": [
                    param.name
                    for param in signature.parameters.values()
                    if param.default is inspect.Parameter.empty
                ],
            },
        },
    }


async def backoff(retries: int, max_jitter: int = 10):
    """Exponential backoff timer with a random jitter."""
    await asyncio.sleep(2**retries + random.random() * max_jitter)  # nosec


async def get_thread_id(slack_id) -> str:
    """
    Get the thread from the user_id or channel.

    Args:
        slack_id: The user or channel id.

    Returns:
        The thread id.
    """
    async with redis.from_url(config.REDIS_URL) as redis_client:
        thread_id = await redis_client.get(slack_id)
        if thread_id:
            thread_id = thread_id.decode()
        else:
            thread = await openai.AsyncOpenAI().beta.threads.create()
            thread_id = thread.id

        await redis_client.set(slack_id, thread_id)

    return thread_id

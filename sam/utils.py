from __future__ import annotations

import asyncio
import enum
import inspect
import logging
import random
import typing

import yaml

logger = logging.getLogger(__name__)

__all__ = ["func_to_tool"]


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
}


def func_to_tool(fn: callable) -> dict:
    """
    Convert a function to an OpenAI tool definition based on signature and docstring.

    The docstring should be formatted using the Google Napolean style.
    """
    signature: inspect.Signature = inspect.signature(fn)
    params = [
        param
        for param in signature.parameters.values()
        if not param.name.startswith("_")
    ]
    if params:
        description, args = fn.__doc__.split("Args:")
        doc_data = yaml.safe_load(args.split("Returns:")[0])
    else:
        description = fn.__doc__
        doc_data = {}

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": "\n".join(
                filter(None, (line.strip() for line in description.splitlines()))
            ),
            "parameters": {
                "type": "object",
                "properties": dict(params_to_props(fn, params, doc_data)),
                "required": [
                    param.name
                    for param in params
                    if param.default is inspect.Parameter.empty
                ],
            },
        },
    }


def params_to_props(fn, params, doc_data):
    types = typing.get_type_hints(fn)
    for param in params:
        param_type = types[param.name]
        if param_type in type_map:
            yield param.name, {
                "type": type_map[types[param.name]],
                "description": doc_data[param.name],
            }
        elif issubclass(param_type, enum.StrEnum):
            yield param.name, {
                "type": "string",
                "enum": [value.value for value in param_type],
                "description": doc_data[param.name],
            }


async def backoff(retries: int, max_jitter: int = 10):
    """Exponential backoff timer with a random jitter."""
    await asyncio.sleep(2**retries + random.random() * max_jitter)  # nosec

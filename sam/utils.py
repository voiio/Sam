from __future__ import annotations

import asyncio
import enum
import importlib
import inspect
import logging
import random
import typing
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

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


def func_to_tool(
    fn_name: str, fn: callable, additional_instructions: str = None
) -> dict:
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
            "name": fn_name,
            "description": "\n".join(
                filter(None, (line.strip() for line in description.splitlines()))
            )
            + (f"\n\n{additional_instructions}" if additional_instructions else ""),
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


@dataclass
class AssistantConfig:
    name: str
    assistant_id: str
    instructions: list[str]
    project: str

    @cached_property
    def system_prompt(self):
        return "\n\n".join(
            Path(instruction).read_text() for instruction in self.instructions
        )


@dataclass
class Tool:
    name: str
    path: str
    additional_instructions: str | None = None
    fn: callable = None

    def __post_init__(self):
        module_name, fn_name = self.path.split(":")
        try:
            self.fn = getattr(importlib.import_module(module_name), fn_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Failed to import {self.path}") from e
        self.declaration: dict = func_to_tool(
            self.name, self.fn, additional_instructions=self.additional_instructions
        )

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

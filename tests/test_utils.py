from __future__ import annotations

import enum

import pytest
from sam import utils

import tests.test_tools


@pytest.mark.asyncio
async def test_backoff():
    await utils.backoff(0, max_jitter=0)


BloodTypes = enum.StrEnum("BloodTypes", {"A": "A", "B": "B"})


def test_func_to_tool():
    def fn(
        a: int, b: str, blood_types: tests.test_utils.BloodTypes, _context=None
    ) -> str:
        """
        Describe function.

        Args:
            a: Description of a.
            b: Description of b.
            blood_types: Description of bool_types.

        Returns:
            Description of return value.
        """
        return a

    tool = utils.func_to_tool("my_unique_function", fn)
    assert tool == {
        "type": "function",
        "function": {
            "name": "my_unique_function",
            "description": "Describe function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "Description of a.",
                    },
                    "b": {
                        "type": "string",
                        "description": "Description of b.",
                    },
                    "blood_types": {
                        "type": "string",
                        "enum": ["A", "B"],
                        "description": "Description of bool_types.",
                    },
                },
                "required": ["a", "b", "blood_types"],
            },
        },
    }


@pytest.mark.asyncio
async def test_async_redis_client():
    async with utils.async_redis_client("redis:///") as client:
        assert await client.ping() is True

    async with utils.async_redis_client("rediss:///", False) as client:
        assert await client.ping() is True

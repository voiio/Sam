from __future__ import annotations

import pytest

from sam import utils


@pytest.mark.asyncio
async def test_backoff():
    await utils.backoff(0, max_jitter=0)


def test_func_to_tool():
    def fn(a: int, b: str) -> int:
        """Function description.

        Args:
            a: Description of a.
            b: Description of b.

        Returns:
            Description of return value.
        """
        return a

    tool = utils.func_to_tool(fn)
    assert tool == {
        "type": "function",
        "function": {
            "name": "fn",
            "description": "Function description.",
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
                },
                "required": ["a", "b"],
            },
        },
    }

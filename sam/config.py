from __future__ import annotations

import enum
import os
import tomllib
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from zoneinfo import ZoneInfo

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis:///")
RANDOM_RUN_RATIO = float(os.getenv("RANDOM_RUN_RATIO", "0"))
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "UTC"))
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
BRAVE_SEARCH_LONGITUDE = os.getenv("BRAVE_SEARCH_LONGITUDE")
BRAVE_SEARCH_LATITUDE = os.getenv("BRAVE_SEARCH_LATITUDE")
SENTRY_DSN = os.getenv("SENTRY_DSN")
GITHUB_REPOS = enum.StrEnum(
    "GITHUB_REPOS",
    {repo: repo for repo in os.getenv("GITHUB_REPOS", "").split(",") if repo},
)


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


def load_assistants():
    with Path("pyproject.toml").open("rb") as fs:
        for assistant in (
            tomllib.load(fs).get("tool", {}).get("sam", {}).get("assistants", [])
        ):
            yield AssistantConfig(**assistant)

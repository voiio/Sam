"""The configuration for your bot.

Config values are loaded from environment variables, and have defaults if not set.
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path
from zoneinfo import ZoneInfo

from sam.utils import AssistantConfig, Tool

_TRUTHY = {"1", "true", "yes", "on"}

# General
#: The URL of the Redis database server.
REDIS_URL: str = os.getenv("REDIS_URL", "redis:///")
#: How often the bot randomly responds in a group channel.
RANDOM_RUN_RATIO: float = float(os.getenv("RANDOM_RUN_RATIO", "0"))
#: The timezone the bot "lives" in.
TIMEZONE: ZoneInfo = ZoneInfo(os.getenv("TIMEZONE", "UTC"))
#: The Brave Search API key for web search.


# OpenAI
#: The OpenAI API key.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
#: The OpenAI assistant ID used for the bot.
OPENAI_ASSISTANT_ID: str = os.getenv("OPENAI_ASSISTANT_ID")
#: The OpenAI model used for text-to-speech.
TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")
#: The OpenAI model used for speech-to-text.
TTS_MODEL: str = os.getenv("TTS_MODEL", "tts-1-hd")
#: Specific words or acronyms for speech-to-text.
STT_PROMPT: str = os.getenv("STT_PROMPT", "")
#: The maximum number of tokens allowed in a prompt.
MAX_PROMPT_TOKENS: int | None = (
    int(os.getenv("MAX_PROMPT_TOKENS")) if "MAX_PROMPT_TOKENS" in os.environ else None
)
#: The maximum number of tokens allowed in a completion.
MAX_COMPLETION_TOKENS: int | None = (
    int(os.getenv("MAX_COMPLETION_TOKENS"))
    if "MAX_COMPLETION_TOKENS" in os.environ
    else None
)

#: The bot will start a fresh thread each day, forgetting the previous day's context.
GROUNDHOG_DAY_MODE: bool = os.getenv("GROUNDHOG_DAY_MODE", "false").lower() in _TRUTHY


# Slack
#: The Slack bot token, prefixed with `xoxb-`.
SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN")
#: The Slack app token, prefixed with `xapp-`.
SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN")

# Email
#: The email address the bot sends emails from.
EMAIL_URL: str | None = os.getenv("EMAIL_URL")
FROM_EMAIL: str | None = os.getenv("FROM_EMAIL")
EMAIL_WHITELIST_PATTERN: re.Pattern | None = (
    re.compile(os.getenv("EMAIL_WHITELIST_PATTERN"))
    if "EMAIL_WHITELIST_PATTERN" in os.environ
    else None
)

# Sentry
#: The Sentry DSN for Sentry based error reporting.
SENTRY_DSN: str = os.getenv("SENTRY_DSN")


def load_tools() -> dict[str, callable]:
    with Path("pyproject.toml").open("rb") as fs:
        for fn_id, config in (
            tomllib.load(fs).get("tool", {}).get("sam", {}).get("tools", {}).items()
        ):
            yield fn_id, Tool(fn_id, **config)


TOOLS = dict(load_tools())


def load_assistants() -> Iterable[AssistantConfig]:
    with Path("pyproject.toml").open("rb") as fs:
        for assistant in (
            tomllib.load(fs).get("tool", {}).get("sam", {}).get("assistants", [])
        ):
            yield AssistantConfig(**assistant)


ASSISTANTS = list(load_assistants())

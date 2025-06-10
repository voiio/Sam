"""The configuration for your bot.

Config values are loaded from environment variables, and have defaults if not set.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}

# General
#: The URL of the Redis database server.
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/")
#: How often the bot randomly responds in a group channel.
RANDOM_RUN_RATIO: float = float(os.getenv("RANDOM_RUN_RATIO", "0"))

# OpenWebUI
#: The OpenWebUI domain URL, without /api at the end.
OPEN_WEBUI_URL: str | None = os.getenv("OPEN_WEBUI_URL")
#: The OpenWebUI API key, used for authentication.
OPEN_WEBUI_API_KEY: str | None = os.getenv("OPEN_WEBUI_API_KEY")
#: The OpenWebUI model to use for chat completions.
OPEN_WEBUI_MODEL: str | None = os.getenv("OPEN_WEBUI_MODEL")

# OpenAI
#: The OpenAI API key.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
#: The OpenAI model used for text-to-speech.
TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")
#: The OpenAI model used for speech-to-text.
TTS_MODEL: str = os.getenv("TTS_MODEL", "tts-1-hd")
#: Specific words or acronyms for speech-to-text.
STT_PROMPT: str = os.getenv("STT_PROMPT", "")

#: The bot will start a fresh thread each day, forgetting the previous day's context.
GROUNDHOG_DAY_MODE: bool = os.getenv("GROUNDHOG_DAY_MODE", "false").lower() in _TRUTHY

# Slack
#: The Slack bot token, prefixed with `xoxb-`.
SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN")
#: The Slack app token, prefixed with `xapp-`.
SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN")

# Sentry
#: The Sentry DSN for Sentry based error reporting.
SENTRY_DSN: str = os.getenv("SENTRY_DSN")

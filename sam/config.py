import enum
import os
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

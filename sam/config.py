import os

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis:///")
RANDOM_RUN_RATIO = float(os.getenv("RANDOM_RUN_RATIO", "0.1"))

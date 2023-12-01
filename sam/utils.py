import functools

import openai
import redis

from . import config

__all__ = ["get_thread_id", "storage"]

storage: redis.Redis = redis.from_url(config.REDIS_URL)


@functools.lru_cache
def get_thread_id(slack_id) -> str:
    """
    Get the thread from the user_id or channel.

    Args:
        slack_id: The user_id or channel id, starting with a '@' or '#'.

    Returns:
        The thread id.
    """
    if slack_id[0] not in ["@", "#"]:
        raise ValueError("The slack_id must start with a '@' or '#'.")

    thread_id = storage.get(slack_id)
    if thread_id:
        thread_id = thread_id.decode()
    else:
        thread_id = openai.beta.threads.create().id

    storage.set(slack_id, thread_id)

    return thread_id

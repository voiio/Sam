from __future__ import annotations

import contextlib

import redis.asyncio as redis
from redis.asyncio.connection import parse_url

from sam import config


@contextlib.asynccontextmanager
async def async_redis_client(url):
    """Asynchronous context manager to get a Redis client."""
    parsed_config = parse_url(url)
    connection_config = {}

    if parsed_config.get("connection_class") == redis.SSLConnection:
        connection_config["ssl_cert_reqs"] = config.REDIS_CERT_REQS

    client = await redis.from_url(url, **connection_config)
    try:
        yield client
    finally:
        await client.aclose()

from __future__ import annotations

import contextlib

import redis.asyncio as redis


@contextlib.asynccontextmanager
async def async_redis_client(url):
    """Asynchronous context manager to get a Redis client."""
    client = await redis.from_url(url)
    try:
        yield client
    finally:
        await client.aclose()

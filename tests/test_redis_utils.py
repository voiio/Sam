from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sam import config, redis_utils


@pytest.mark.asyncio
async def test_async_redis_client(monkeypatch):
    with patch("redis.asyncio.from_url", AsyncMock()) as redis_mock:
        async with redis_utils.async_redis_client("redis:///") as client:
            assert client
            redis_mock.assert_called_once_with("redis:///")
            redis_mock.reset_mock()

        async with redis_utils.async_redis_client("rediss:///") as client:
            assert client
            redis_mock.assert_called_once_with("rediss:///", ssl_cert_reqs="required")
            redis_mock.reset_mock()

        monkeypatch.setattr(config, "REDIS_CERT_REQS", "none")
        async with redis_utils.async_redis_client("rediss:///") as client:
            assert client
            redis_mock.assert_called_once_with("rediss:///", ssl_cert_reqs="none")
            redis_mock.reset_mock()

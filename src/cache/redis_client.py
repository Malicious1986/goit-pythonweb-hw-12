from typing import Dict
import asyncio
import redis.asyncio as aioredis

from src.conf.config import config


_clients: Dict[int, aioredis.Redis] = {}


def get_redis() -> aioredis.Redis:
    """Return an asyncio Redis client scoped to the current event loop.

    If no running event loop is available, return a transient client.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return aioredis.from_url(
            config.REDIS_URL, encoding="utf-8", decode_responses=True
        )

    key = id(loop)
    client = _clients.get(key)
    if client is None:
        client = aioredis.from_url(
            config.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        _clients[key] = client
    return client

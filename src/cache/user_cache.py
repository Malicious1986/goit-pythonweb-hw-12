import json
from typing import Optional

from src.cache.redis_client import get_redis
from src.conf.config import config


async def set_user_cache(user: dict) -> None:
    """Store user dict in redis under `user:{username}` with TTL."""
    r = get_redis()
    key = f"user:{user['username']}"

    await r.set(key, json.dumps(user), ex=config.CACHE_TTL)


async def get_user_cache(username: str) -> Optional[dict]:
    """Return cached user dict or None."""
    r = get_redis()
    key = f"user:{username}"
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


async def delete_user_cache(username: str) -> None:
    r = get_redis()
    key = f"user:{username}"
    await r.delete(key)

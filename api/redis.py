from aioredis import Redis, from_url

from api.config import settings
from functools import lru_cache


@lru_cache()
async def init_redis_pool() -> Redis:
    redis = await from_url(
        settings.redis_url,
        encoding="utf-8",
        db=settings.redis_db_name,
        decode_responses=True,
    )
    return redis

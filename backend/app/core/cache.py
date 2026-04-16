"""Optional Redis cache. When REDIS_DSN is set, get/set use Redis; otherwise get returns None."""

from app.core.config import settings
from app.core.logging import logger

_redis_client = None


def _get_redis():
    """Lazy Redis connection. Returns None if REDIS_DSN is not set."""
    global _redis_client
    if not settings.REDIS_DSN or not settings.REDIS_DSN.strip():
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(
                settings.REDIS_DSN.strip(),
                decode_responses=True,
            )
        except Exception as exc:
            logger.warning("redis_connect_failed", error=str(exc))
            _redis_client = False  # mark as failed so we don't retry every time
    return _redis_client if _redis_client is not False else None


async def cache_get(key: str) -> str | None:
    """Get value from cache. Returns None if cache is disabled or key missing."""
    client = _get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        logger.warning("redis_get_failed", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: str, ttl_seconds: int = 300) -> None:
    """Set value in cache with TTL. No-op if cache is disabled."""
    client = _get_redis()
    if client is None:
        return
    try:
        await client.setex(key, ttl_seconds, value)
    except Exception as exc:
        logger.warning("redis_set_failed", key=key, error=str(exc))

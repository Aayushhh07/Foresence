import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis = None


async def connect_redis() -> None:
    """Connect to Upstash Redis."""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.upstash_redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=10,
    )
    # Verify connection
    await _redis_client.ping()
    logger.info("Connected to Redis successfully.")


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        logger.info("Redis connection closed.")


def get_redis() -> aioredis.Redis:
    """Return the active Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call connect_redis() first.")
    return _redis_client


async def acquire_zone_lock(zone_id: str, ttl_seconds: int = 39600) -> bool:
    """
    Attempt to acquire a distributed lock for a zone scan.
    Returns True if lock acquired, False if zone is already being scanned.
    TTL default: 11 hours (39600 seconds)
    """
    client = get_redis()
    key = f"zone_lock:{zone_id}"
    result = await client.set(key, "locked", ex=ttl_seconds, nx=True)
    return result is True


async def release_zone_lock(zone_id: str) -> None:
    """Release an existing zone scan lock."""
    client = get_redis()
    key = f"zone_lock:{zone_id}"
    await client.delete(key)


async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Set a cached value with TTL."""
    client = get_redis()
    await client.set(key, value, ex=ttl_seconds)


async def cache_get(key: str) -> str | None:
    """Get a cached value."""
    client = get_redis()
    return await client.get(key)

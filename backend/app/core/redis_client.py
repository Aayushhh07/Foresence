import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None

# In-memory fallback when Redis is not configured
_memory_locks: dict = {}


async def connect_redis() -> None:
    """Connect to Redis. If URL is empty or invalid, fall back to in-memory mode."""
    global _redis_client

    url = settings.upstash_redis_url.strip()

    # Check if a real URL was provided
    if not url or not any(url.startswith(s) for s in ("redis://", "rediss://", "unix://")):
        logger.warning(
            "UPSTASH_REDIS_URL is not set or invalid — running in memory-only mode. "
            "Zone locks will be in-process only (fine for single-worker dev)."
        )
        _redis_client = None
        return

    try:
        _redis_client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
        )
        await _redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Redis connection failed ({e}) — falling back to in-memory mode.")
        _redis_client = None


async def close_redis() -> None:
    """Close Redis connection if open."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        logger.info("Redis connection closed.")


def get_redis() -> Optional[aioredis.Redis]:
    """Return the active Redis client, or None if running in memory-only mode."""
    return _redis_client


async def acquire_zone_lock(zone_id: str, ttl_seconds: int = 39600) -> bool:
    """
    Acquire a distributed lock for a zone scan.
    Falls back to an in-memory dict when Redis is unavailable.
    Returns True if lock acquired, False if zone is already being scanned.
    """
    if _redis_client is not None:
        key = f"zone_lock:{zone_id}"
        result = await _redis_client.set(key, "locked", ex=ttl_seconds, nx=True)
        return result is True
    else:
        # In-memory fallback (single-process only)
        if zone_id in _memory_locks:
            return False
        _memory_locks[zone_id] = True
        return True


async def release_zone_lock(zone_id: str) -> None:
    """Release an existing zone scan lock."""
    if _redis_client is not None:
        key = f"zone_lock:{zone_id}"
        await _redis_client.delete(key)
    else:
        _memory_locks.pop(zone_id, None)


async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Set a cached value with TTL. No-op in memory-only mode."""
    if _redis_client is not None:
        await _redis_client.set(key, value, ex=ttl_seconds)


async def cache_get(key: str) -> Optional[str]:
    """Get a cached value. Returns None in memory-only mode."""
    if _redis_client is not None:
        return await _redis_client.get(key)
    return None

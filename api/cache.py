"""
Redis cache layer for Persona Platform.

Provides async caching with graceful degradation when Redis is unavailable.
All operations silently fail (return None/False) rather than raising exceptions.
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger("persona_hub.cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class CacheManager:
    _client: Optional[redis.Redis] = None
    _available: Optional[bool] = None  # None = untested, True/False = known state

    async def get_client(self) -> Optional[redis.Redis]:
        """Lazy-init Redis client. Returns None if Redis is unavailable."""
        if self._client is None:
            try:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
                # Ping to verify connectivity
                await self._client.ping()
                self._available = True
                logger.info("Redis connected: %s", REDIS_URL)
            except Exception as exc:
                logger.warning("Redis unavailable (%s) — cache disabled", exc)
                self._client = None
                self._available = False
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if missing / Redis unavailable."""
        client = await self.get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug("Cache GET error for %r: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Store value in cache with TTL (seconds). No-op if Redis unavailable."""
        client = await self.get_client()
        if client is None:
            return
        try:
            serialized = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized)
        except Exception as exc:
            logger.debug("Cache SET error for %r: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Delete a single cache key."""
        client = await self.get_client()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception as exc:
            logger.debug("Cache DELETE error for %r: %s", key, exc)

    async def exists(self, key: str) -> bool:
        """Return True if key exists in cache."""
        client = await self.get_client()
        if client is None:
            return False
        try:
            result = await client.exists(key)
            return bool(result)
        except Exception as exc:
            logger.debug("Cache EXISTS error for %r: %s", key, exc)
            return False

    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern. Returns count of deleted keys."""
        client = await self.get_client()
        if client is None:
            return 0
        try:
            keys = await client.keys(pattern)
            if not keys:
                return 0
            count = await client.delete(*keys)
            return count
        except Exception as exc:
            logger.debug("Cache FLUSH_PATTERN error for %r: %s", pattern, exc)
            return 0

    async def info(self) -> Optional[dict]:
        """Return Redis INFO stats dict, or None if unavailable."""
        client = await self.get_client()
        if client is None:
            return None
        try:
            raw = await client.info()
            return raw
        except Exception as exc:
            logger.debug("Cache INFO error: %s", exc)
            return None

    async def dbsize(self) -> int:
        """Return total number of keys in the Redis database."""
        client = await self.get_client()
        if client is None:
            return 0
        try:
            return await client.dbsize()
        except Exception:
            return 0

    async def flushdb(self) -> None:
        """Flush the entire Redis database. Use with caution."""
        client = await self.get_client()
        if client is None:
            return
        try:
            await client.flushdb()
        except Exception as exc:
            logger.warning("Cache FLUSHDB error: %s", exc)

    @property
    def is_available(self) -> bool:
        """Returns True if Redis was successfully connected (tested at least once)."""
        return self._available is True


# ── Cache key helpers ─────────────────────────────────────────────────────────

def persona_catalog_key() -> str:
    """Cache key for the full persona catalog listing."""
    return "persona:catalog"


def persona_vector_key(persona_id: str) -> str:
    """Cache key for a single persona's vector data."""
    return f"persona:vector:{persona_id}"


def user_purchases_key(user_id: str) -> str:
    """Cache key for a user's purchase list."""
    return f"user:purchases:{user_id}"


def feature_flags_key() -> str:
    """Cache key for all feature flags."""
    return "feature:flags:all"


# ── Decorator ─────────────────────────────────────────────────────────────────

def cached(key_fn, ttl: int = 3600):
    """
    Async function cache decorator.

    Usage:
        @cached(key_fn=lambda *a, **kw: f"mykey:{a[0]}", ttl=600)
        async def my_func(arg): ...

    key_fn receives the same positional/keyword arguments as the decorated
    function and must return a string cache key.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            key = key_fn(*args, **kwargs)
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


# ── Global instance ───────────────────────────────────────────────────────────

_cache = CacheManager()


async def get_cache() -> CacheManager:
    """FastAPI dependency / standalone accessor for the global CacheManager."""
    return _cache

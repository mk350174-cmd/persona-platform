"""Cache Management Router — Redis cache stats and control endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Any, Dict

from api.db import get_db, User
from api.auth import get_current_user
from api.cache import get_cache, CacheManager

router = APIRouter(prefix="/cache", tags=["cache"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_admin(user: User) -> User:
    """Raise 403 if the authenticated user is not an admin."""
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def cache_health(cache: CacheManager = Depends(get_cache)):
    """
    Check Redis connectivity.

    Returns connection status and basic ping latency without requiring auth.
    """
    import time

    client = await cache.get_client()
    if client is None:
        return {
            "status": "unavailable",
            "redis_url": "configured",
            "message": "Redis is not reachable — caching is disabled",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        t0 = time.monotonic()
        await client.ping()
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "message": "Redis is healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/stats")
async def cache_stats(
    user: User = Depends(get_current_user),
    cache: CacheManager = Depends(get_cache),
):
    """
    Redis INFO — memory usage, hit/miss rates, and key count.

    Requires authentication (any role).
    """
    info = await cache.info()
    if info is None:
        return {
            "available": False,
            "message": "Redis is not reachable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    key_count = await cache.dbsize()

    # Extract the most useful fields from Redis INFO
    stats: Dict[str, Any] = {
        "available": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "key_count": key_count,
        "memory": {
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio"),
        },
        "stats": {
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
        },
        "server": {
            "redis_version": info.get("redis_version"),
            "os": info.get("os"),
            "tcp_port": info.get("tcp_port"),
        },
    }

    # Calculate hit rate when data is available
    hits = stats["stats"]["keyspace_hits"]
    misses = stats["stats"]["keyspace_misses"]
    total = hits + misses
    stats["stats"]["hit_rate_pct"] = round(hits / total * 100, 2) if total > 0 else None

    return stats


@router.delete("/flush")
async def flush_all_cache(
    user: User = Depends(get_current_user),
    cache: CacheManager = Depends(get_cache),
    db: Session = Depends(get_db),
):
    """
    Flush the entire Redis cache.

    **Admin only.** Removes all keys from the current Redis database.
    Use with caution in production.
    """
    _require_admin(user)

    client = await cache.get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Redis is not available")

    key_count_before = await cache.dbsize()
    await cache.flushdb()

    return {
        "flushed": True,
        "keys_removed": key_count_before,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "performed_by": user.id,
    }


@router.delete("/personas")
async def flush_persona_cache(
    user: User = Depends(get_current_user),
    cache: CacheManager = Depends(get_cache),
):
    """
    Flush persona-related cache entries only.

    Removes all keys matching `persona:*` (catalog + vector cache).
    Requires authentication (any role).
    """
    deleted = await cache.flush_pattern("persona:*")

    return {
        "flushed": True,
        "pattern": "persona:*",
        "keys_removed": deleted,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

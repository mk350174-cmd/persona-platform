"""
Unit tests for api/cache.py — Redis cache with graceful degradation.

No real Redis: an injected fake client exercises the happy path, and
monkeypatching `redis.from_url` to raise exercises the unavailable path
(where every op returns the safe default).
"""

import asyncio

import pytest

import api.cache as cache_mod
from api.cache import (
    CacheManager,
    persona_catalog_key,
    persona_vector_key,
    user_purchases_key,
    feature_flags_key,
    cached,
    get_cache,
)


def _run(coro):
    return asyncio.run(coro)


# ── fake redis client ────────────────────────────────────────────────────────

class _FakeRedis:
    def __init__(self):
        self.store = {}
    async def ping(self): return True
    async def get(self, k): return self.store.get(k)
    async def setex(self, k, ttl, v): self.store[k] = v
    async def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]; n += 1
        return n
    async def exists(self, k): return 1 if k in self.store else 0
    async def keys(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]
    async def info(self): return {"redis_version": "7.0"}
    async def dbsize(self): return len(self.store)
    async def flushdb(self): self.store.clear()


def _available_manager():
    cm = CacheManager()
    cm._client = _FakeRedis()
    cm._available = True
    return cm


# ── happy path (fake client injected) ────────────────────────────────────────

def test_set_get_roundtrip():
    cm = _available_manager()
    _run(cm.set("k", {"a": 1}, ttl=60))
    assert _run(cm.get("k")) == {"a": 1}


def test_get_missing_returns_none():
    cm = _available_manager()
    assert _run(cm.get("absent")) is None


def test_delete_and_exists():
    cm = _available_manager()
    _run(cm.set("k", "v"))
    assert _run(cm.exists("k")) is True
    _run(cm.delete("k"))
    assert _run(cm.exists("k")) is False


def test_flush_pattern():
    cm = _available_manager()
    _run(cm.set("persona:vector:a", 1))
    _run(cm.set("persona:vector:b", 2))
    _run(cm.set("other", 3))
    assert _run(cm.flush_pattern("persona:vector:*")) == 2
    assert _run(cm.exists("other")) is True


def test_flush_pattern_no_match_returns_zero():
    cm = _available_manager()
    assert _run(cm.flush_pattern("nope:*")) == 0


def test_info_dbsize_flushdb():
    cm = _available_manager()
    _run(cm.set("k", "v"))
    assert _run(cm.info())["redis_version"] == "7.0"
    assert _run(cm.dbsize()) == 1
    _run(cm.flushdb())
    assert _run(cm.dbsize()) == 0


def test_is_available_property():
    cm = _available_manager()
    assert cm.is_available is True
    assert CacheManager().is_available is False   # untested → False


# ── error path within ops (client raises) ────────────────────────────────────

class _BoomRedis(_FakeRedis):
    async def get(self, k): raise RuntimeError("boom")
    async def setex(self, k, ttl, v): raise RuntimeError("boom")
    async def delete(self, *k): raise RuntimeError("boom")
    async def exists(self, k): raise RuntimeError("boom")
    async def keys(self, p): raise RuntimeError("boom")
    async def info(self): raise RuntimeError("boom")
    async def dbsize(self): raise RuntimeError("boom")
    async def flushdb(self): raise RuntimeError("boom")


def test_op_errors_degrade_gracefully():
    cm = CacheManager()
    cm._client = _BoomRedis()
    cm._available = True
    assert _run(cm.get("k")) is None
    _run(cm.set("k", "v"))            # swallowed
    _run(cm.delete("k"))             # swallowed
    assert _run(cm.exists("k")) is False
    assert _run(cm.flush_pattern("*")) == 0
    assert _run(cm.info()) is None
    assert _run(cm.dbsize()) == 0
    _run(cm.flushdb())               # swallowed


# ── unavailable path (connection fails) ──────────────────────────────────────

def test_unavailable_returns_safe_defaults(monkeypatch):
    def _boom(*a, **k):
        raise ConnectionError("no redis")
    monkeypatch.setattr(cache_mod.redis, "from_url", _boom)
    cm = CacheManager()
    assert _run(cm.get("k")) is None
    _run(cm.set("k", "v"))
    _run(cm.delete("k"))
    assert _run(cm.exists("k")) is False
    assert _run(cm.flush_pattern("*")) == 0
    assert _run(cm.info()) is None
    assert _run(cm.dbsize()) == 0
    _run(cm.flushdb())
    assert cm.is_available is False


# ── key helpers ──────────────────────────────────────────────────────────────

def test_key_helpers():
    assert persona_catalog_key() == "persona:catalog"
    assert persona_vector_key("socrates") == "persona:vector:socrates"
    assert user_purchases_key("u1") == "user:purchases:u1"
    assert feature_flags_key() == "feature:flags:all"


# ── cached decorator ─────────────────────────────────────────────────────────

def test_cached_decorator_memoizes(monkeypatch):
    fake = _available_manager()

    async def _get_fake():
        return fake
    monkeypatch.setattr(cache_mod, "get_cache", _get_fake)

    calls = {"n": 0}

    @cached(key_fn=lambda arg: f"mykey:{arg}", ttl=60)
    async def expensive(arg):
        calls["n"] += 1
        return {"value": arg}

    assert _run(expensive("x")) == {"value": "x"}
    assert _run(expensive("x")) == {"value": "x"}   # served from cache
    assert calls["n"] == 1                            # underlying fn ran once


def test_cached_decorator_skips_none(monkeypatch):
    fake = _available_manager()

    async def _get_fake():
        return fake
    monkeypatch.setattr(cache_mod, "get_cache", _get_fake)

    @cached(key_fn=lambda arg: f"none:{arg}")
    async def returns_none(arg):
        return None

    assert _run(returns_none("x")) is None
    # None results are not cached
    assert _run(fake.get("none:x")) is None


def test_get_cache_returns_global_singleton():
    assert _run(get_cache()) is _run(get_cache())

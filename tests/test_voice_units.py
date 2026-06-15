"""
Unit tests for api/voice.py — ElevenLabs TTS wrapper.

Pure helpers tested directly; the async synth functions are exercised with the
key forced on/off and httpx patched, so no real network is hit.
"""

import asyncio
import sys
import types

import pytest

import api.voice as voice


# ── pure helpers ─────────────────────────────────────────────────────────────

def test_get_voice_id_known_and_default():
    assert voice._get_voice_id("machiavelli") == voice.PERSONA_VOICE_IDS["machiavelli"]
    assert voice._get_voice_id("unknown_persona") == voice.DEFAULT_VOICE_ID


def test_audio_cache_path_deterministic_and_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "AUDIO_CACHE_DIR", tmp_path)
    p1 = voice._audio_cache_path("hello", "holmes", "{}")
    p2 = voice._audio_cache_path("hello", "holmes", "{}")
    p3 = voice._audio_cache_path("different", "holmes", "{}")
    assert p1 == p2            # deterministic
    assert p1 != p3            # text changes the digest
    assert p1.name.startswith("holmes_") and p1.suffix == ".mp3"


def test_tts_available_reflects_key(monkeypatch):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "")
    assert voice.tts_available() is False
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")
    assert voice.tts_available() is True


# ── synthesize_speech ────────────────────────────────────────────────────────

def test_synthesize_speech_no_key_returns_none(monkeypatch):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "")
    assert asyncio.run(voice.synthesize_speech("hi", "holmes")) is None


def test_synthesize_speech_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")
    monkeypatch.setattr(voice, "AUDIO_CACHE_DIR", tmp_path)
    # pre-seed the cache file for the exact key
    params = {"stability": 0.65, "similarity_boost": 0.75, "style_exaggeration": 0.2}
    cache = voice._audio_cache_path("hi", "holmes", str(params))
    cache.write_bytes(b"CACHED_MP3")
    out = asyncio.run(voice.synthesize_speech("hi", "holmes"))
    assert out == b"CACHED_MP3"


def test_synthesize_speech_calls_api_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")
    monkeypatch.setattr(voice, "AUDIO_CACHE_DIR", tmp_path)

    class _Resp:
        content = b"FRESH_MP3"
        def raise_for_status(self): pass

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None): return _Resp()

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = _Client
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    out = asyncio.run(voice.synthesize_speech("brand new", "machiavelli"))
    assert out == b"FRESH_MP3"
    # cached to disk
    cached = voice._audio_cache_path("brand new", "machiavelli",
                                     str({"stability": 0.65, "similarity_boost": 0.75, "style_exaggeration": 0.2}))
    assert cached.exists() and cached.read_bytes() == b"FRESH_MP3"


def test_synthesize_speech_api_error_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")
    monkeypatch.setattr(voice, "AUDIO_CACHE_DIR", tmp_path)

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): raise RuntimeError("network down")

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = _Client
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    assert asyncio.run(voice.synthesize_speech("x", "holmes")) is None


# ── synthesize_stream ────────────────────────────────────────────────────────

def _drain(agen):
    async def _collect():
        return [chunk async for chunk in agen]
    return asyncio.run(_collect())


def test_synthesize_stream_no_key_yields_nothing(monkeypatch):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "")
    assert _drain(voice.synthesize_stream("hi", "holmes")) == []


def test_synthesize_stream_yields_chunks(monkeypatch):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")

    class _Resp:
        def raise_for_status(self): pass
        async def aiter_bytes(self, chunk_size=4096):
            for c in (b"a", b"b", b"c"):
                yield c

    class _StreamCtx:
        async def __aenter__(self): return _Resp()
        async def __aexit__(self, *a): return False

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, method, url, json=None, headers=None): return _StreamCtx()

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = _Client
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    assert _drain(voice.synthesize_stream("hi", "machiavelli")) == [b"a", b"b", b"c"]


def test_synthesize_stream_falls_back_on_error(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ELEVENLABS_API_KEY", "el_key")
    monkeypatch.setattr(voice, "AUDIO_CACHE_DIR", tmp_path)

    # streaming client raises → fallback to synthesize_speech (patched to return bytes)
    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **k): raise RuntimeError("no stream")

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = _Client
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    async def _fake_synth(text, persona_id, voice_params=None):
        return b"FALLBACK"
    monkeypatch.setattr(voice, "synthesize_speech", _fake_synth)

    assert _drain(voice.synthesize_stream("hi", "holmes")) == [b"FALLBACK"]

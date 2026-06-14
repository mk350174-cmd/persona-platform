"""
Unit tests for api/needle_service.py — PersonaNeedle bridge with persona_math fallback.

We force the fallback path (PersonaNeedle/torch route raises) by patching get_needle,
so the tests assert the deterministic persona_math reference behaviour regardless of
whether torch is installed.
"""

import numpy as np
import pytest

import api.needle_service as ns


# ── helpers ──────────────────────────────────────────────────────────────────

def test_k_layer_known_and_unknown():
    P = ns._k_layer("socrates")
    assert P is not None and P.shape == (100,)
    assert ns._k_layer("definitely_unknown_xyz") is None


def test_ceid_reference_axes():
    P = ns._k_layer("socrates")
    ref = ns._ceid_reference(P)
    assert set(ref) >= {"C", "E", "I", "D", "composite"}
    assert all(0.0 <= float(v) <= 1.0 for v in ref.values())


# ── measure_ceid (fallback forced) ───────────────────────────────────────────

@pytest.fixture
def force_fallback(monkeypatch):
    def _raise(_pid):
        raise RuntimeError("torch/PersonaNeedle unavailable")
    monkeypatch.setattr(ns, "get_needle", _raise)


def test_measure_ceid_fallback(force_fallback):
    out = ns.measure_ceid("socrates", "a short test")
    assert set("CEID") <= set(out)
    assert out["untrained"] is True
    assert "persona_math" in out["source"]
    assert "composite" in out


def test_measure_ceid_unknown_persona(force_fallback):
    out = ns.measure_ceid("definitely_unknown_xyz", "x")
    assert out["untrained"] is True
    assert out.get("error") == "unknown persona"


def test_detect_drift_fallback(force_fallback):
    out = ns.detect_drift("socrates", "x")
    assert out["degraded"] is True
    assert out["untrained"] is True
    assert out["drift"] is None


def test_generate_voice_fallback(force_fallback):
    out = ns.generate_voice("socrates", "hello")
    assert out["degraded"] is True
    assert out["voice"] is None

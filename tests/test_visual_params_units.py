"""
Unit tests for api/visual_params.py — HPEP-100 → avatar parameter bridge.

Pure numerical transforms (no DB, no network), so these run on every Python
version and in parallel without isolation concerns.
"""

import numpy as np
import pytest

from api.visual_params import (
    _block_mean,
    _clamp,
    compute_visual_params,
    get_visual_params,
    compute_speech_delta,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _vec(val=0.5):
    return np.full(100, val, dtype=float)


# ── _block_mean / _clamp ─────────────────────────────────────────────────────

def test_block_mean_full_block():
    P = _vec(0.5)
    assert _block_mean(P, 1) == pytest.approx(0.5)
    assert _block_mean(P, 10) == pytest.approx(0.5)


def test_block_mean_distinct_blocks():
    P = np.zeros(100)
    P[0:10] = 1.0          # block 1 all ones
    assert _block_mean(P, 1) == pytest.approx(1.0)
    assert _block_mean(P, 2) == pytest.approx(0.0)


def test_block_mean_short_vector_truncates():
    P = np.ones(5)
    # block 1 wants indices 0..10 but only 5 exist → mean over what's there
    assert _block_mean(P, 1) == pytest.approx(1.0)


def test_block_mean_empty_segment_returns_zero():
    P = np.ones(5)
    # block 2 starts at index 10, beyond len → empty → 0.0
    assert _block_mean(P, 2) == 0.0


def test_clamp_bounds():
    assert _clamp(-1.0) == 0.0
    assert _clamp(2.0) == 1.0
    assert _clamp(0.42) == pytest.approx(0.42)
    assert _clamp(5.0, lo=1.0, hi=3.0) == 3.0


# ── compute_visual_params ────────────────────────────────────────────────────

def test_compute_visual_params_defaults_and_ranges():
    out = compute_visual_params(_vec(0.5))
    # all scalar params in [0,1]
    scalar_keys = [
        "posture_dominance", "face_hardness", "consciousness_ring",
        "active_neurons", "drift_tremor", "speech_intensity",
        "contemplation_depth", "ambient_light", "eye_contact",
        "power_axis", "ethics_axis",
    ]
    for k in scalar_keys:
        assert 0.0 <= out[k] <= 1.0, f"{k} out of range: {out[k]}"
    for k in ("stability", "similarity_boost", "style_exaggeration"):
        assert 0.0 <= out["voice"][k] <= 1.0


def test_compute_visual_params_defaults_ceid_and_gwt():
    # ceid_score None → 0.8 ; gwt None → 60
    out = compute_visual_params(_vec(0.5))
    assert out["consciousness_ring"] == pytest.approx(0.8)   # _clamp(0.8)
    assert out["active_neurons"] == pytest.approx(0.6)       # 60/100


def test_compute_visual_params_drift_tremor_passthrough():
    out = compute_visual_params(_vec(0.5), drift_val=0.42)
    assert out["drift_tremor"] == pytest.approx(0.42)
    # drift clamps above 1
    assert compute_visual_params(_vec(0.5), drift_val=9.0)["drift_tremor"] == 1.0


def test_compute_visual_params_nano_tier_has_no_particle_color():
    out = compute_visual_params(_vec(0.5), tier="nano")
    assert "particle_color" not in out
    assert "block_profile" not in out


def test_compute_visual_params_standard_tier_has_particle_color():
    out = compute_visual_params(_vec(0.5), tier="standard")
    assert set(out["particle_color"]) == {"r", "g", "b"}
    assert "block_profile" not in out


def test_compute_visual_params_rich_tier_full_profile():
    out = compute_visual_params(_vec(0.5), ceid_score=0.91, gwt_firing_count=70, tier="rich")
    assert "particle_color" in out
    assert "block_profile" in out
    assert set(out["block_profile"]) == {f"b{i}" for i in range(1, 11)}
    assert out["ceid_score"] == pytest.approx(0.91)
    assert "core_health" in out
    assert out["active_neurons"] == pytest.approx(0.7)


def test_compute_visual_params_short_vector_core_fallback():
    # len(P) <= 11 → core_keys = [P[0]] branch
    out = compute_visual_params(np.ones(5), tier="rich")
    assert out["core_health"] == pytest.approx(1.0)


def test_get_visual_params_wrapper_matches_compute():
    P = _vec(0.3)
    assert get_visual_params(P, persona_id="socrates", tier="standard") == \
        compute_visual_params(P, tier="standard")


# ── compute_speech_delta ─────────────────────────────────────────────────────

def test_speech_delta_reports_only_significant_changes():
    prev = compute_visual_params(_vec(0.2))
    curr = compute_visual_params(_vec(0.8))
    delta = compute_speech_delta(prev, curr)
    # at least one scalar moved > 0.01
    assert delta
    assert all(abs(v) > 0.01 for v in delta.values())


def test_speech_delta_ignores_tiny_changes():
    prev = {"posture_dominance": 0.500}
    curr = {"posture_dominance": 0.505}   # 0.005 < 0.01 threshold
    assert compute_speech_delta(prev, curr) == {}


def test_speech_delta_skips_missing_keys():
    # keys absent in one dict are skipped without error
    assert compute_speech_delta({}, {"face_hardness": 0.9}) == {}

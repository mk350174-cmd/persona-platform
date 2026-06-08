"""
PersonaNeedle SAN tests.

Torch-free tests (parameter / size estimators) always run — they verify the ~26M budget
and the honest INT4 size analytically. The model/init/shape tests require torch and skip
cleanly where it is not installed (e.g. this repo's CI environment).
"""

import pytest

from needle.architecture.config import (
    PersonaNeedleConfig, estimate_param_count, estimate_int4_size_mb, estimate_fp32_size_mb,
)

try:
    import torch  # noqa: F401
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")

CFG = PersonaNeedleConfig(persona_id="generic")
TARGET, TOL = 26_000_000, 0.10


# ── torch-free: parameter & size budget ──────────────────────────────────────────

def test_param_count_estimate_within_10pct():
    n = estimate_param_count(CFG)
    assert TARGET * (1 - TOL) <= n <= TARGET * (1 + TOL), f"{n:,} not within 26M ±10%"


def test_int4_size_is_real_compression():
    int4, fp32 = estimate_int4_size_mb(CFG), estimate_fp32_size_mb(CFG)
    assert int4 < fp32 * 0.3                 # genuine 4-bit compression (~0.125)
    assert 5.0 < int4 < 15.0                  # honest ~13MB at 26M (not <10MB)


def test_config_validation():
    with pytest.raises(ValueError):
        PersonaNeedleConfig(hidden_dim=500, num_heads=8)   # not divisible
    with pytest.raises(ValueError):
        PersonaNeedleConfig(num_heads=8, kv_heads=3)        # GQA mismatch


# ── torch-required: model init / shapes / pipeline / actual size ─────────────────

@requires_torch
def test_model_init_and_actual_param_count():
    from needle.architecture.san import SAN
    model = SAN(CFG)
    actual = model.num_parameters()
    assert actual == estimate_param_count(CFG)                 # estimator matches model exactly
    assert TARGET * (1 - TOL) <= actual <= TARGET * (1 + TOL)


@requires_torch
def test_forward_head_shapes():
    import torch
    from needle.architecture.san import SAN
    model = SAN(CFG).eval()
    B, T, Td = 2, 16, 8
    persona = torch.randn(B, CFG.k_layer_dim)
    ids = torch.randint(0, CFG.vocab_size, (B, T))
    dec = torch.randint(0, CFG.vocab_size, (B, Td))
    with torch.no_grad():
        out = model(persona, ids, decoder_input_ids=dec)
    assert out["ceid"].shape == (B, 4)                          # CEID 4-dim
    assert float(out["ceid"].min()) >= 0.0 and float(out["ceid"].max()) <= 1.0
    assert out["drift_logits"].shape == (B, 2)                  # binary drift
    assert out["voice_logits"].shape == (B, Td, CFG.vocab_size) # voice logits


@requires_torch
def test_persona_needle_methods():
    from needle import PersonaNeedle
    pn = PersonaNeedle(CFG)
    c = pn.measure_ceid("a short test conversation")
    assert set(("C", "E", "I", "D")).issubset(c) and all(0.0 <= c[a] <= 1.0 for a in "CEID")
    d = pn.detect_drift("a short test conversation")
    assert isinstance(d["drift"], bool) and 0.0 <= d["score"] <= 1.0
    assert isinstance(pn.generate_voice("hello", max_new_tokens=8), str)
    fp = pn.full_pipeline("conv", "prompt")
    assert {"persona_id", "ceid", "drift", "voice", "untrained"} <= set(fp)


@requires_torch
def test_quantized_size_report():
    from needle.architecture.san import SAN
    from needle.architecture.quantizer import size_report
    rep = size_report(SAN(CFG))
    assert rep["int4_mb"] < rep["fp32_mb"] * 0.3
    assert rep["n_params"] == estimate_param_count(CFG)

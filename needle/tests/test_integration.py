"""PersonaNeedle ↔ persona_math integration (torch-guarded)."""

import pytest

from needle.architecture.config import PersonaNeedleConfig

try:
    import torch  # noqa: F401
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")


@requires_torch
def test_reference_ceid_from_persona_math():
    from needle import PersonaNeedle
    pn = PersonaNeedle(PersonaNeedleConfig(persona_id="socrates"))
    ref = pn.reference_ceid()                      # uses persona_math.ceid.ceid_score
    assert set(("C", "E", "I", "D")) <= set(ref["axes"])
    assert 0.0 <= ref["composite"] <= 1.0
    assert "persona_math" in ref["source"]


@requires_torch
def test_measure_vs_reference_same_axes():
    from needle import PersonaNeedle
    pn = PersonaNeedle(PersonaNeedleConfig(persona_id="socrates"))
    measured = pn.measure_ceid("test conversation")
    ref = pn.reference_ceid()
    # same axis namespace (the SAN head is distilled toward the reference)
    assert set("CEID") <= set(measured) and set("CEID") <= set(ref["axes"])
    assert measured["untrained"] is True           # untrained until distilled


def test_distillation_data_builder_torch_free():
    # building reference labels needs only persona_math (no torch)
    from needle.architecture.distillation import build_training_data
    examples = list(build_training_data(limit=5))
    assert len(examples) == 5
    for ex in examples:
        assert ex.ceid_label.shape == (4,)
        assert ex.persona_vector.shape[0] == PersonaNeedleConfig().k_layer_dim

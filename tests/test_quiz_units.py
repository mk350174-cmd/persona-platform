"""
Unit tests for api/quiz_service.py — the HPEP quiz scoring engine.

Torch-free and API-free: open-ended scoring falls back to a neutral prior when
ANTHROPIC_API_KEY is unset, so these tests are deterministic without network.
"""

import numpy as np
import pytest

from api import quiz_service as qs
from api.quiz_questions import (
    QUESTION_BANK,
    public_question_bank,
    get_question,
    N_QUESTIONS_TOTAL,
)


@pytest.fixture(autouse=True)
def _no_anthropic(monkeypatch):
    # Force the API-free fallback path for open-ended scoring.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _all_agree():
    """Answer every structured question with the top Likert option (index 4)."""
    return {q["id"]: 4 for q in QUESTION_BANK if q["type"] == "structured"}


def _all_disagree():
    return {q["id"]: 0 for q in QUESTION_BANK if q["type"] == "structured"}


# ── vector shape / range ────────────────────────────────────────────────────────

def test_vector_shape_and_range():
    P = qs.build_persona_vector(_all_agree())
    assert P.shape == (100,)
    assert P.dtype == float or np.issubdtype(P.dtype, np.floating)
    assert float(P.min()) >= 0.0 and float(P.max()) <= 1.0


def test_empty_answers_returns_base_vector():
    P = qs.build_persona_vector({})
    assert P.shape == (100,)
    # No answers → population prior centred on base (0.5) with mild seeded variance.
    assert abs(float(P.mean()) - 0.5) < 0.05
    assert float(P.min()) >= 0.0 and float(P.max()) <= 1.0


# ── structured answers move the right layers ────────────────────────────────────

def test_agree_raises_targeted_layers():
    P_hi = qs.build_persona_vector(_all_agree())
    P_lo = qs.build_persona_vector(_all_disagree())
    # Q1 targets K-index 0 and 7; "strongly agree" should exceed "strongly disagree".
    assert P_hi[0] > P_lo[0]
    assert P_hi[7] > P_lo[7]


def test_option_by_label_and_index_equivalent():
    by_index = qs.build_persona_vector({"Q1": 4})
    label = get_question("Q1")["options"][4]["label"]
    by_label = qs.build_persona_vector({"Q1": label})
    assert np.allclose(by_index, by_label)


def test_invalid_option_ignored():
    # Out-of-range index and unknown label must not raise; treated as unanswered,
    # so the result is identical to the no-answer vector (same seed → same noise).
    P = qs.build_persona_vector({"Q1": 99, "Q2": "nonsense"})
    assert np.allclose(P, qs.build_persona_vector({}))


# ── CEID extraction ─────────────────────────────────────────────────────────────

def test_extract_persona_keys():
    out = qs.extract_persona(_all_agree())
    assert set(out) >= {"k_layer", "ceid", "n_answered", "n_total", "source", "untrained"}
    assert len(out["k_layer"]) == 100
    assert out["untrained"] is True
    ceid = out["ceid"]
    assert set("CEID") <= set(ceid)
    assert "composite" in ceid and "classification" in ceid
    for axis in "CEID":
        assert 0.0 <= ceid[axis] <= 1.0


def test_n_answered_counts_only_answered():
    out = qs.extract_persona({"Q1": 4, "Q2": 2})
    assert out["n_answered"] == 2
    assert out["n_total"] == len(QUESTION_BANK)


# ── open-ended fallback ─────────────────────────────────────────────────────────

def test_open_ended_neutral_without_api_key():
    # Q50 is open-ended; without an API key it scores 0.5 (neutral).
    score = qs._score_open_ended(get_question("Q50"), "Some thoughtful answer.")
    assert score == 0.5


def test_open_ended_empty_answer_is_neutral():
    assert qs._score_open_ended(get_question("Q50"), "") == 0.5


def test_open_answer_projects_onto_target_layers():
    # Answering Q50 (targets K100 idx 99) should set those layers toward 0.5.
    P = qs.build_persona_vector({"Q50": "I choose to keep my commitments."})
    assert abs(P[99] - 0.5) < 1e-6


# ── question bank hygiene ────────────────────────────────────────────────────────

def test_public_bank_hides_weights():
    pub = public_question_bank()
    assert len(pub) == len(QUESTION_BANK)
    for item in pub:
        assert "layers" not in item
        if item["type"] == "structured":
            for o in item["options"]:
                assert set(o) == {"label"}


def test_axis_layers_indices_valid():
    for axis, idxs in qs.AXIS_LAYERS.items():
        assert axis in "CEID"
        assert all(0 <= i < 100 for i in idxs)


def test_protocol_length_constant():
    assert N_QUESTIONS_TOTAL == 50

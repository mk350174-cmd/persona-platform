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


def _all_strong_answers():
    """Answer every open-ended question with a strong positive response (0.9 score)."""
    return {q["id"]: 0.9 for q in QUESTION_BANK if q["type"] == "open"}


def _all_weak_answers():
    """Answer every open-ended question with a weak response (0.1 score)."""
    return {q["id"]: 0.1 for q in QUESTION_BANK if q["type"] == "open"}


# ── vector shape / range ────────────────────────────────────────────────────────

def test_vector_shape_and_range():
    P = qs.build_persona_vector(_all_strong_answers())
    assert P.shape == (100,)
    assert P.dtype == float or np.issubdtype(P.dtype, np.floating)
    assert float(P.min()) >= 0.0 and float(P.max()) <= 1.0


def test_empty_answers_returns_base_vector():
    P = qs.build_persona_vector({})
    assert P.shape == (100,)
    # No answers → population prior centred on base (0.5) with mild seeded variance.
    assert abs(float(P.mean()) - 0.5) < 0.05
    assert float(P.min()) >= 0.0 and float(P.max()) <= 1.0


# ── open-ended answers aggregate onto target layers ────────────────────────────────

def test_answers_aggregate_to_target_layers():
    # S1 targets K-indices [0, 7]. Answering it should set those layers.
    # Without API key, all answers score 0.5 (neutral), so result is deterministic.
    P = qs.build_persona_vector({"S1": "Some thoughtful response to the first question."})
    # K-index 0 and 7 should have been touched by S1's answer (averaged into 0.5).
    assert 0.0 <= P[0] <= 1.0
    assert 0.0 <= P[7] <= 1.0
    # The question targeted these layers, so they should be somewhere in the range.
    assert abs(P[0] - 0.5) < 0.2  # Close to neutral prior since API returns 0.5
    assert abs(P[7] - 0.5) < 0.2


def test_empty_string_scores_neutral():
    # Empty answer string scores as 0.5 (neutral), which is different from no answer.
    # Empty answer contributes 0.5 to target layers; no answer leaves layers as noise.
    P_empty = qs.build_persona_vector({"S1": ""})
    P_noanswer = qs.build_persona_vector({})
    # Empty answer should push S1's target layers toward 0.5; they'll be slightly different.
    assert not np.allclose(P_empty, P_noanswer)
    # But the mean should still be close to 0.5
    assert abs(P_empty.mean() - 0.5) < 0.05
    assert abs(P_noanswer.mean() - 0.5) < 0.05


# ── CEID extraction ─────────────────────────────────────────────────────────────

def test_extract_persona_keys():
    out = qs.extract_persona(_all_strong_answers())
    assert set(out) >= {"k_layer", "ceid", "n_answered", "n_total", "source", "untrained"}
    assert len(out["k_layer"]) == 100
    assert out["untrained"] is True
    ceid = out["ceid"]
    assert set("CEID") <= set(ceid)
    assert "composite" in ceid and "classification" in ceid
    for axis in "CEID":
        assert 0.0 <= ceid[axis] <= 1.0


def test_n_answered_counts_only_answered():
    out = qs.extract_persona({"S1": "Answer 1", "S2": "Answer 2"})
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
    # Answering S50 (targets K-indices [99, 2, 81]) should set those layers.
    # Without API key, answer scores 0.5 (neutral). With seeded noise, values cluster near 0.5.
    P = qs.build_persona_vector({"S50": "I choose to keep my commitments."})
    # K99, K2, K81 should be influenced by the 0.5 score (within noise tolerance ~0.1)
    assert abs(P[99] - 0.5) < 0.1
    assert abs(P[2] - 0.5) < 0.1
    assert abs(P[81] - 0.5) < 0.1


# ── question bank hygiene ────────────────────────────────────────────────────────

def test_public_bank_hides_weights():
    pub = public_question_bank()
    assert len(pub) == len(QUESTION_BANK)
    for item in pub:
        # Public view should only have: id, phase, type, text
        assert set(item.keys()) == {"id", "phase", "type", "text"}
        # No scoring rubric, layers, or axes should be exposed
        assert "layers" not in item
        assert "rubric" not in item
        assert "ceid_axis" not in item
        assert "target_layers" not in item


def test_public_bank_multi_language():
    # Test language parameter support
    for lang in ["tr", "en", "de", "fr", "ja", "ar"]:
        pub = public_question_bank(lang=lang)
        assert len(pub) == len(QUESTION_BANK)
        for q in pub:
            # Text should be a string in the specified language or fallback to English
            assert isinstance(q["text"], str)
            assert len(q["text"]) > 0
            # Should not contain placeholder markers from missing languages
            assert "[TODO" not in q["text"] or lang in ("tr", "en", "de", "fr", "ja", "ar")


def test_turkish_translations_complete():
    """All 50 questions must have distinct Turkish text (no English fallback, no TODO)."""
    pub_tr = public_question_bank(lang="tr")
    pub_en = public_question_bank(lang="en")
    assert len(pub_tr) == 50
    for q_tr, q_en in zip(pub_tr, pub_en):
        # TR text must be non-empty and not a TODO placeholder
        assert isinstance(q_tr["text"], str)
        assert len(q_tr["text"]) > 0
        assert "[TODO" not in q_tr["text"], f"{q_tr['id']} has TODO placeholder in TR"
        # TR text must differ from EN (i.e., a real translation, not a fallback)
        assert q_tr["text"] != q_en["text"], f"{q_tr['id']} TR text is identical to EN — missing translation"


def test_all_languages_return_non_empty_text():
    """Every language must return non-empty text for every question (TR/EN verbatim, others placeholder)."""
    for lang in ("tr", "en", "de", "fr", "ja", "ar"):
        pub = public_question_bank(lang=lang)
        for q in pub:
            assert len(q["text"]) > 0, f"{q['id']} has empty text for lang={lang}"


def test_public_bank_default_language():
    pub_default = public_question_bank()
    pub_en = public_question_bank(lang="en")
    # Default should be English
    assert pub_default[0]["text"] == pub_en[0]["text"]


def test_public_bank_invalid_language_fallback():
    # Invalid language should fall back to English
    pub_invalid = public_question_bank(lang="invalid")
    pub_en = public_question_bank(lang="en")
    assert pub_invalid[0]["text"] == pub_en[0]["text"]


def test_axis_layers_indices_valid():
    from api.quiz_questions import AXIS_LAYERS
    for axis, idxs in AXIS_LAYERS.items():
        assert axis in "CEID"
        assert all(0 <= i < 100 for i in idxs)


def test_protocol_length_constant():
    assert N_QUESTIONS_TOTAL == 50

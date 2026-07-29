"""
Tests for the AIML / Groq / OpenRouter teachers + pipeline weight normalization.

Torch-free and SDK-free: the API clients are built lazily, so these import and run without
the openai/groq SDKs. API calls are mocked via ``_ask``; the persona_math fallback is
exercised by making ``_ask`` raise.
"""

import pytest

from needle.training.teachers import AIMLTeacher, GroqTeacher, OpenRouterTeacher
from needle.training.pipeline import TrainingPipeline

TEACHERS = [AIMLTeacher, GroqTeacher, OpenRouterTeacher]
PV = [0.5] * 100        # a K-layer persona vector


@pytest.mark.parametrize("cls", TEACHERS)
def test_available_reflects_key(cls):
    assert cls("").available() is False          # no key → unavailable
    assert cls("a-key").available() is True       # key present → available (no SDK needed)


@pytest.mark.parametrize("cls", TEACHERS)
def test_weights_match_spec(cls):
    assert {AIMLTeacher: 0.5, GroqTeacher: 0.3, OpenRouterTeacher: 0.2}[cls] == cls("k").weight


@pytest.mark.parametrize("cls", TEACHERS)
def test_generate_ceid_labels_with_mock(cls):
    t = cls("k")
    t._ask = lambda prompt: '{"C": 0.8, "E": 0.7, "I": 0.6, "D": 0.9}'   # mock API
    labels = t.generate_ceid_labels("socrates", PV, "a conversation")
    assert labels == {"C": 0.8, "E": 0.7, "I": 0.6, "D": 0.9}


@pytest.mark.parametrize("cls", TEACHERS)
def test_ceid_falls_back_to_persona_math_on_error(cls):
    t = cls("k")

    def boom(prompt):
        raise RuntimeError("API down")

    t._ask = boom
    labels = t.generate_ceid_labels("socrates", PV, "a conversation")   # fallback path
    assert set("CEID").issubset(labels)
    assert all(0.0 <= labels[a] <= 1.0 for a in "CEID")


@pytest.mark.parametrize("cls", TEACHERS)
def test_drift_falls_back_on_error(cls):
    t = cls("k")
    t._ask = lambda prompt: (_ for _ in ()).throw(RuntimeError("API down"))
    d = t.generate_drift_label("socrates", "before", {"text": "after", "pressure": 3})
    assert isinstance(d["drift"], bool) and 0.0 <= d["score"] <= 1.0


# ── pipeline weight normalization ────────────────────────────────────────────────

def test_pipeline_three_teachers_normalized():
    pipe = TrainingPipeline(aiml_api_key="a", groq_api_key="g", openrouter_api_key="o",
                            llama_endpoint=None)
    names = set(pipe.teacher_names())
    assert {"aiml", "groq", "openrouter"} <= names          # real teachers active
    assert "persona_math" in names                          # + always-on co-teacher (weight 0.1)
    assert sum(t.weight for t in pipe.teachers) == pytest.approx(1.0, abs=1e-3)  # 6-dp rounding


def test_pipeline_subset_normalized_to_one():
    pipe = TrainingPipeline(aiml_api_key="a", groq_api_key="g", llama_endpoint=None)  # 0.5+0.3
    assert "persona_math" in pipe.teacher_names()           # co-teacher present (weight 0.1)
    assert sum(t.weight for t in pipe.teachers) == pytest.approx(1.0)


def test_persona_math_coteacher_weight():
    pipe = TrainingPipeline(groq_api_key="g", llama_endpoint=None)   # groq 0.3 + persona_math 0.1
    weights = {t.name: t.weight for t in pipe.teachers}
    assert set(weights) == {"groq", "persona_math"}
    assert weights["persona_math"] == pytest.approx(0.1 / 0.4)       # 0.25 after normalization
    assert weights["groq"] == pytest.approx(0.3 / 0.4)              # 0.75


def test_pipeline_no_keys_falls_back_to_persona_math():
    pipe = TrainingPipeline(llama_endpoint=None)            # no keys, no Ollama
    assert pipe.teacher_names() == ["persona_math"]
    assert pipe.teachers[0].weight == pytest.approx(1.0)


def test_groq_rate_limit_is_1s():
    # rpm 30 → 60 : 60/60 = 1s between requests
    assert GroqTeacher("k").rate.min_interval == pytest.approx(1.0)
    assert GroqTeacher.rpm == 60
    assert GroqTeacher.model == "llama-3.1-8b-instant"   # 8B-instant (was 70b-versatile)


def test_rate_limiter_is_thread_safe():
    # the builder runs conversations in parallel → the limiter must serialize across threads
    import threading
    from needle.training.teachers._remote import RateLimiter
    assert isinstance(RateLimiter(60)._lock, type(threading.Lock()))

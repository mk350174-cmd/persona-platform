"""
Extra tests targeting the Anthropic API scoring path in api/quiz_service.py.

These tests exercise _score_open_ended when ANTHROPIC_API_KEY is set, using a
mock Anthropic client injected via monkeypatch so no real network call is made.
"""

import pytest

from api import quiz_service as qs
from api.quiz_questions import get_question


# ── Mock helpers ───────────────────────────────────────────────────────────────

def _make_mock_anthropic_client(text_response: str):
    """Return a mock `anthropic.Anthropic` class that yields `text_response`."""

    class _ContentItem:
        def __init__(self, text):
            self.text = text

    class _Message:
        def __init__(self, text):
            self.content = [_ContentItem(text)]

    class _Messages:
        def __init__(self, text):
            self._text = text

        def create(self, **kwargs):
            return _Message(self._text)

    class _MockClient:
        def __init__(self, **kwargs):
            self.messages = _Messages(text_response)

    return _MockClient


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestScoreOpenEndedWithApiKey:
    """Tests that require ANTHROPIC_API_KEY to be set (monkeypatched)."""

    def test_valid_float_response_returned(self, monkeypatch):
        """API responds with '0.75' → function returns 0.75."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("0.75")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "A thoughtful and detailed answer.")
        assert result == pytest.approx(0.75, abs=1e-6)

    def test_result_clamped_above_one(self, monkeypatch):
        """API responds with '1.5' (out of range) → clamped to 1.0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("1.5")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Very strong answer.")
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_result_clamped_below_zero(self, monkeypatch):
        """API responds with '-0.2' → clamped to 0.0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("-0.2")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Poor answer.")
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_response_with_leading_text_parsed(self, monkeypatch):
        """API returns '0.82 is the score' → first token '0.82' parsed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("0.82 is the score")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Good answer text.")
        assert result == pytest.approx(0.82, abs=1e-6)

    def test_zero_score_returned(self, monkeypatch):
        """API responds with '0.0' → exactly 0.0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("0.0")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Minimal answer.")
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_one_score_returned(self, monkeypatch):
        """API responds with '1.0' → exactly 1.0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("1.0")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Perfect answer.")
        assert result == pytest.approx(1.0, abs=1e-6)


class TestScoreOpenEndedErrorHandling:
    """Tests that the function degrades gracefully when the API fails."""

    def test_unparseable_response_returns_neutral(self, monkeypatch):
        """API returns non-numeric text → fallback to 0.5."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        MockClient = _make_mock_anthropic_client("not a number at all")
        monkeypatch.setattr("anthropic.Anthropic", MockClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Some answer.")
        assert result == 0.5

    def test_api_exception_returns_neutral(self, monkeypatch):
        """Exception during API call → fallback to 0.5."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")

        class _BrokenClient:
            def __init__(self, **kwargs):
                pass
            @property
            def messages(self):
                raise RuntimeError("Network failure")

        monkeypatch.setattr("anthropic.Anthropic", _BrokenClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Some answer.")
        assert result == 0.5

    def test_import_error_returns_neutral(self, monkeypatch):
        """If anthropic module is not importable → fallback to 0.5."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")

        # Simulate import failure by making Anthropic raise on instantiation
        def _bad_import(**kwargs):
            raise ImportError("No module named 'anthropic'")

        monkeypatch.setattr("anthropic.Anthropic", _bad_import)

        question = get_question("S50")
        result = qs._score_open_ended(question, "Some answer.")
        assert result == 0.5

    def test_empty_answer_short_circuits_before_api(self, monkeypatch):
        """Empty answer returns 0.5 without touching the API."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        call_count = []

        class _TrackingClient:
            def __init__(self, **kwargs):
                call_count.append(1)

        monkeypatch.setattr("anthropic.Anthropic", _TrackingClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "")
        assert result == 0.5
        assert len(call_count) == 0, "Anthropic client should not be instantiated for empty answer"

    def test_whitespace_only_answer_is_neutral(self, monkeypatch):
        """Whitespace-only answer strips to empty → 0.5 without API call."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        call_count = []

        class _TrackingClient:
            def __init__(self, **kwargs):
                call_count.append(1)

        monkeypatch.setattr("anthropic.Anthropic", _TrackingClient)

        question = get_question("S50")
        result = qs._score_open_ended(question, "   \t  \n  ")
        assert result == 0.5
        assert len(call_count) == 0


class TestScoreOpenEndedNoApiKey:
    """Confirm that without API key the function returns 0.5 regardless of answer."""

    @pytest.fixture(autouse=True)
    def _no_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def test_no_key_returns_neutral(self):
        question = get_question("S50")
        assert qs._score_open_ended(question, "Detailed multi-paragraph answer.") == 0.5

    def test_no_key_empty_answer_neutral(self):
        question = get_question("S50")
        assert qs._score_open_ended(question, "") == 0.5

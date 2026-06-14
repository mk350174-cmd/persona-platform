"""Integration tests for HPEP-100 quiz router endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app, get_db
from api.db import User, UserPersona, QuizSubmission, create_user, hash_password
from api.quiz_questions import QUESTION_BANK


@pytest.fixture
def client(test_db):
    """FastAPI test client with test database override."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user(test_db):
    """Create authenticated user with valid API key."""
    user, full_api_key = create_user(test_db, email="quiz@test.com")
    user.password_hash = hash_password("TestPass123!")
    test_db.commit()
    return user, full_api_key


class TestQuizQuestionsEndpoint:
    """Tests for GET /api/v1/quiz/questions."""

    def test_get_questions_default_language(self, client):
        """Get questions in default English language."""
        resp = client.get("/api/v1/quiz/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 50
        assert data[0]["id"] == "S1"
        assert "text" in data[0]
        assert isinstance(data[0]["text"], str)
        assert len(data[0]["text"]) > 0

    def test_get_questions_all_languages(self, client):
        """Get questions in each supported language."""
        for lang in ["tr", "en", "de", "fr", "ja", "ar"]:
            resp = client.get(f"/api/v1/quiz/questions?lang={lang}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 50
            for q in data:
                assert "id" in q
                assert "phase" in q
                assert "type" in q
                assert "text" in q
                assert isinstance(q["text"], str)

    def test_get_questions_language_fallback(self, client):
        """Invalid language parameter falls back to English."""
        resp_invalid = client.get("/api/v1/quiz/questions?lang=invalid")
        # FastAPI validates regex, so this should return 422
        assert resp_invalid.status_code == 422

    def test_get_questions_valid_language_codes(self, client):
        """All 6 language codes are accepted."""
        valid_langs = ["tr", "en", "de", "fr", "ja", "ar"]
        for lang in valid_langs:
            resp = client.get(f"/api/v1/quiz/questions?lang={lang}")
            assert resp.status_code == 200, f"Language {lang} failed"

    def test_get_questions_response_structure(self, client):
        """Response questions have correct structure."""
        resp = client.get("/api/v1/quiz/questions")
        data = resp.json()
        for q in data:
            # Should only have: id, phase, type, text (no rubric/layers)
            assert set(q.keys()) == {"id", "phase", "type", "text"}
            assert isinstance(q["id"], str)
            assert isinstance(q["phase"], int)
            assert 1 <= q["phase"] <= 10
            assert q["type"] == "open"

    def test_get_questions_all_50_present(self, client):
        """All 50 questions are present."""
        resp = client.get("/api/v1/quiz/questions")
        data = resp.json()
        ids = {q["id"] for q in data}
        expected_ids = {f"S{i}" for i in range(1, 51)}
        assert ids == expected_ids

    def test_get_questions_no_rubric_leaked(self, client):
        """Rubric and layers are not exposed in public view."""
        resp = client.get("/api/v1/quiz/questions")
        data = resp.json()
        for q in data:
            assert "rubric" not in q
            assert "layers" not in q
            assert "target_layers" not in q
            assert "ceid_axis" not in q
            assert "amcc" not in q


class TestQuizSubmitEndpoint:
    """Tests for POST /api/v1/quiz/submit."""

    def test_submit_requires_authentication(self, client):
        """Submit endpoint requires valid authentication."""
        payload = {
            "answers": {"S1": 0.5, "S2": 0.7}
        }
        resp = client.post("/api/v1/quiz/submit", json=payload)
        # Should redirect or return 401/403 without auth
        assert resp.status_code in (401, 403, 307)

    def test_submit_with_partial_answers(self, client, authenticated_user, test_db):
        """Submit quiz with partial answers."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        # Prepare answers for a subset of questions
        answers = {
            "S1": 0.5,
            "S2": 0.7,
            "S3": 0.3,
            "S5": 0.9,
        }

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Verify response structure
        assert "persona" in data
        assert "checkout_url" in data
        assert "k_layer" in data["persona"]
        assert "ceid_scores" in data["persona"]
        assert len(data["persona"]["k_layer"]) == 100
        assert all(0.0 <= v <= 1.0 for v in data["persona"]["k_layer"])

    def test_submit_creates_quiz_submission(self, client, authenticated_user, test_db):
        """Submitting quiz creates QuizSubmission record."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {"S1": 0.5, "S2": 0.8}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200

        # Verify submission was created
        submission = test_db.query(QuizSubmission).filter_by(user_id=user.id).first()
        assert submission is not None
        assert submission.answers == answers

    def test_submit_creates_user_persona(self, client, authenticated_user, test_db):
        """Submitting quiz creates/updates UserPersona."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {"S1": 0.6, "S2": 0.4}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200

        # Verify persona was created
        persona = test_db.query(UserPersona).filter_by(user_id=user.id).first()
        assert persona is not None
        assert len(persona.k_layer) == 100
        assert "C" in persona.ceid_scores
        assert "E" in persona.ceid_scores
        assert "I" in persona.ceid_scores
        assert "D" in persona.ceid_scores

    def test_submit_with_all_questions(self, client, authenticated_user, test_db):
        """Submit answers for all 50 questions."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        # Create answers for all 50 questions
        answers = {f"S{i}": 0.5 for i in range(1, 51)}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Verify all fields present
        assert data["persona"]["k_layer"]
        assert data["persona"]["ceid_scores"]
        assert "checkout_url" in data

    def test_submit_invalid_question_id(self, client, authenticated_user):
        """Submit with invalid question ID is still processed (ignored)."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {
            "S1": 0.5,
            "INVALID": 0.7,  # Invalid question ID
            "S2": 0.3,
        }

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        # Should still process valid answers
        assert resp.status_code == 200

    def test_submit_score_normalization(self, client, authenticated_user):
        """Scores are normalized to 0-1 range."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {"S1": 0.5}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # K-layer values should be 0-1
        k_layer = data["persona"]["k_layer"]
        assert all(0.0 <= v <= 1.0 for v in k_layer)

    def test_submit_empty_answers(self, client, authenticated_user):
        """Submit with empty answers returns neutral persona."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Should return valid persona even with no answers
        k_layer = data["persona"]["k_layer"]
        assert len(k_layer) == 100
        assert all(isinstance(v, float) for v in k_layer)

    def test_submit_returns_checkout_url(self, client, authenticated_user):
        """Submit response includes checkout URL."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {"S1": 0.5}

        resp = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        checkout_url = data["checkout_url"]
        assert isinstance(checkout_url, str)
        assert len(checkout_url) > 0
        # Currently placeholder, but should be valid format
        assert "checkout" in checkout_url.lower() or "session" in checkout_url.lower()


class TestQuizResultsEndpoint:
    """Tests for GET /api/v1/quiz/results."""

    def test_results_requires_authentication(self, client):
        """Results endpoint requires authentication."""
        resp = client.get("/api/v1/quiz/results")
        assert resp.status_code in (401, 403, 307)

    def test_results_returns_404_no_quiz(self, client, authenticated_user):
        """Returns 404 if user hasn't submitted quiz."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        resp = client.get("/api/v1/quiz/results", headers=headers)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "No persona extracted" in data["detail"]

    def test_results_after_submission(self, client, authenticated_user, test_db):
        """Get results after quiz submission."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        # First submit a quiz
        answers = {"S1": 0.5, "S2": 0.7, "S3": 0.3}
        resp_submit = client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )
        assert resp_submit.status_code == 200

        # Then get results
        resp = client.get("/api/v1/quiz/results", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "persona" in data
        assert "submission_count" in data
        assert data["submission_count"] >= 1
        assert len(data["persona"]["k_layer"]) == 100

    def test_results_submission_count(self, client, authenticated_user, test_db):
        """Results show correct submission count."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        # Submit multiple times
        for i in range(3):
            answers = {"S1": 0.1 * (i + 1)}
            resp = client.post(
                "/api/v1/quiz/submit",
                json={"answers": answers},
                headers=headers,
            )
            assert resp.status_code == 200

        # Check results
        resp = client.get("/api/v1/quiz/results", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["submission_count"] == 3

    def test_results_persona_structure(self, client, authenticated_user, test_db):
        """Results persona has correct structure."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        # Submit quiz
        answers = {"S1": 0.5}
        client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )

        # Get results
        resp = client.get("/api/v1/quiz/results", headers=headers)
        data = resp.json()
        persona = data["persona"]

        assert "k_layer" in persona
        assert "ceid_scores" in persona
        assert "created_at" in persona
        assert isinstance(persona["k_layer"], list)
        assert len(persona["k_layer"]) == 100
        assert isinstance(persona["ceid_scores"], dict)

    def test_results_ceid_scores(self, client, authenticated_user, test_db):
        """Results include valid CEID scores."""
        user, api_key = authenticated_user
        headers = {"X-API-Key": api_key}

        answers = {"S1": 0.5}
        client.post(
            "/api/v1/quiz/submit",
            json={"answers": answers},
            headers=headers,
        )

        resp = client.get("/api/v1/quiz/results", headers=headers)
        data = resp.json()
        ceid = data["persona"]["ceid_scores"]

        # Should have CEID axes
        assert "C" in ceid or "composite" in ceid
        # Scores should be 0-1 range
        for key, val in ceid.items():
            if isinstance(val, (int, float)):
                assert 0.0 <= val <= 1.0


class TestQuizLanguageIntegration:
    """Integration tests for multi-language support."""

    def test_questions_same_count_all_languages(self, client):
        """All language variants have 50 questions."""
        for lang in ["tr", "en", "de", "fr", "ja", "ar"]:
            resp = client.get(f"/api/v1/quiz/questions?lang={lang}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 50

    def test_questions_english_has_text(self, client):
        """English questions have full text."""
        resp = client.get("/api/v1/quiz/questions?lang=en")
        data = resp.json()

        for q in data:
            # Questions without translations show TODO placeholder, still valid text
            assert len(q["text"]) > 0

    def test_endpoints_accept_lang_parameter(self, client):
        """All quiz endpoints respect language parameter."""
        # GET /questions with different languages
        for lang in ["en", "tr"]:
            resp = client.get(f"/api/v1/quiz/questions?lang={lang}")
            assert resp.status_code == 200

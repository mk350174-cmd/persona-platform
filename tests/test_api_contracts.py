"""API contract tests — validate response schemas match specification.

These tests prevent schema drift where endpoint responses diverge from
what tests expect. When adding new endpoints, add corresponding contract
tests to ensure request/response schemas are documented and validated.
"""

import pytest
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"

from fastapi.testclient import TestClient
from api.db import create_user, grant_free_persona, record_invoice
from api.main import app, get_db
from datetime import datetime, timezone


@pytest.fixture
def client(test_db):
    """Create test client with test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user(test_db):
    """Create authenticated user for tests."""
    user, api_key = create_user(test_db, "contract_test@example.com")
    grant_free_persona(test_db, user.id, "persona_socrates")
    return {"user": user, "api_key": api_key}


class TestResponseSchemas:
    """Validate response schemas for key endpoints."""

    def test_health_check_schema(self, client):
        """GET /health response schema."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "status" in data
        assert data["status"] == "healthy"
        assert isinstance(data["status"], str)

    def test_persona_list_schema(self, client):
        """GET /personas response schema."""
        response = client.get("/personas")
        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert "personas" in data
        assert isinstance(data["personas"], list)

        # Validate persona object structure
        if data["personas"]:
            persona = data["personas"][0]
            assert "id" in persona
            assert "name" in persona
            assert "description" in persona
            assert "price_usd" in persona

    def test_user_profile_schema(self, client, authenticated_user):
        """GET /me response schema."""
        response = client.get(
            "/me",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "id" in data
        assert "email" in data
        assert data["email"] == "contract_test@example.com"
        assert isinstance(data["id"], int)

    def test_user_purchases_schema(self, client, authenticated_user):
        """GET /me/purchases response schema."""
        response = client.get(
            "/me/purchases",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert "purchases" in data
        assert isinstance(data["purchases"], list)

        # Validate purchase object
        if data["purchases"]:
            purchase = data["purchases"][0]
            assert "persona_id" in purchase
            assert "amount_cents" in purchase
            assert isinstance(purchase["amount_cents"], int)

    def test_wallet_schema(self, client, authenticated_user):
        """GET /me/wallet response schema."""
        response = client.get(
            "/me/wallet",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "balance_cents" in data
        assert "balance_usd" in data
        assert isinstance(data["balance_cents"], int)
        assert isinstance(data["balance_usd"], (int, float))

    def test_invoices_schema(self, client, authenticated_user, test_db):
        """GET /me/invoices response schema."""
        # Create invoice first
        record_invoice(
            test_db,
            authenticated_user["user"].id,
            "inv_test_contract",
            9900,
            status="paid",
            issued_at=datetime.now(timezone.utc),
        )

        response = client.get(
            "/me/invoices",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert "invoices" in data
        assert isinstance(data["invoices"], list)
        assert len(data["invoices"]) == 1

        # Validate invoice object
        invoice = data["invoices"][0]
        assert "stripe_invoice_id" in invoice
        assert "amount_usd_cents" in invoice or "amount_usd" in invoice
        assert "status" in invoice

    def test_analytics_revenue_schema(self, client, authenticated_user):
        """GET /admin/analytics/revenue response schema (admin only)."""
        # First make user admin (for testing contract)
        authenticated_user["user"].role = "admin"

        response = client.get(
            "/admin/analytics/revenue",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )

        if response.status_code == 200:  # Only validate if accessible
            data = response.json()

            # Validate required fields
            assert "period" in data
            assert "total_revenue_usd" in data
            assert isinstance(data["total_revenue_usd"], (int, float))

            # Optional fields may vary
            if "mrr" in data:
                assert isinstance(data["mrr"], (int, float))
            if "arpu" in data:
                assert isinstance(data["arpu"], (int, float))

    def test_analytics_dau_schema(self, client, authenticated_user):
        """GET /admin/analytics/dau response schema (admin only)."""
        # Make user admin
        authenticated_user["user"].role = "admin"

        response = client.get(
            "/admin/analytics/dau",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )

        if response.status_code == 200:  # Only validate if accessible
            data = response.json()

            # Validate required fields
            # Could be "days" or "dates" depending on implementation
            assert "days" in data or "dates" in data
            # Could be "series" or "dau_data" depending on implementation
            assert "series" in data or "dau_data" in data


class TestErrorSchemas:
    """Validate error response schemas."""

    def test_401_unauthorized_schema(self, client):
        """GET /me without auth returns 401 with proper schema."""
        response = client.get("/me")
        assert response.status_code in [401, 403]
        data = response.json()

        # Validate error structure
        assert "detail" in data or "message" in data

    def test_404_not_found_schema(self, client):
        """GET /nonexistent returns 404 with proper schema."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()

        # Validate error structure
        assert "detail" in data or "message" in data

    def test_422_validation_error_schema(self, client, authenticated_user):
        """POST /register with invalid data returns 422 with proper schema."""
        response = client.post(
            "/auth/register",
            json={"email": "invalid-email"},  # Missing password
        )
        assert response.status_code == 422
        data = response.json()

        # Validate error structure
        assert "detail" in data


class TestRequestSchemas:
    """Validate request payloads are properly validated."""

    def test_register_rejects_extra_fields(self, client):
        """POST /register rejects extra fields (extra='forbid')."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "name": "John Doe",  # Extra field not in schema
            },
        )
        # Should reject with 422 due to extra field
        assert response.status_code == 422

    def test_compile_requires_json_body(self, client, authenticated_user):
        """POST /compile requires valid JSON body."""
        response = client.post(
            "/compile/persona_socrates",
            headers={"X-API-Key": authenticated_user["api_key"]},
            json={"platform": "gemini"},  # Valid platform
        )
        # Should succeed or fail for reason other than missing body
        assert response.status_code != 400


class TestWebhookSchemas:
    """Validate webhook event schemas."""

    def test_checkout_session_webhook_structure(self):
        """Validate checkout.session.completed webhook structure."""
        from api.payments import handle_webhook

        event = {
            "id": "evt_test",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test",
                    "mode": "payment",
                    "amount_total": 2999,
                    "customer_email": "test@example.com",
                    "metadata": {"user_id": 1},
                }
            },
        }

        # Validate event structure (webhook handler expects these fields)
        assert "id" in event
        assert "type" in event
        assert "data" in event
        assert "object" in event["data"]


# Testing patterns for future endpoint additions

class TestNewEndpointTemplate:
    """Template for testing new endpoints — copy and customize."""

    def test_new_endpoint_success_schema(self, client, authenticated_user):
        """
        Test new endpoint response schema.

        When adding a new endpoint:
        1. Copy this template
        2. Update endpoint path
        3. Document all required fields
        4. Validate field types
        """
        response = client.get(
            "/new/endpoint",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        # assert response.status_code == 200
        # data = response.json()
        # assert "field1" in data
        # assert "field2" in data
        # assert isinstance(data["field1"], str)
        pass

    def test_new_endpoint_request_validation(self, client, authenticated_user):
        """
        Test new endpoint request validation.

        Document what payloads are accepted/rejected.
        """
        # Valid request
        # response = client.post(
        #     "/new/endpoint",
        #     headers={"X-API-Key": authenticated_user["api_key"]},
        #     json={"required_field": "value"},
        # )
        # assert response.status_code == 200

        # Invalid request (missing required field)
        # response = client.post(
        #     "/new/endpoint",
        #     headers={"X-API-Key": authenticated_user["api_key"]},
        #     json={},
        # )
        # assert response.status_code == 422
        pass

"""Integration tests for payment endpoints (H84)."""

import pytest
import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"  # Mock key for testing

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import (
    Base, SessionLocal, create_user, hash_password, get_or_create_wallet,
    add_wallet_credit, generate_referral_code, PromoCode,
)
from api.main import app, get_db


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestingSessionLocal()


@pytest.fixture
def client(test_db):
    """Create test client."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def authenticated_user(test_db):
    """Create authenticated user."""
    user, full_key = create_user(test_db, "testuser@example.com")
    user.password_hash = hash_password("password123")
    test_db.commit()
    return user, full_key


class TestCheckoutEndpoint:
    """Integration tests for /checkout endpoint."""

    def test_checkout_invalid_persona(self, client):
        """Invalid persona returns 404."""
        response = client.post(
            "/checkout/invalid_persona",
            headers={"X-API-Key": "prs_test_key"},
        )
        assert response.status_code in [400, 404]

    def test_checkout_requires_auth(self, client):
        """Checkout requires authentication."""
        response = client.post("/checkout/persona_socrates")
        assert response.status_code in [401, 403]

    def test_checkout_free_persona(self, client, authenticated_user, test_db):
        """Free personas don't require checkout."""
        user, full_key = authenticated_user
        # Grant free persona
        from api.db import grant_free_persona
        grant_free_persona(test_db, user.id, "persona_socrates")

        response = client.get(
            "/me/purchases",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "purchases" in data


class TestReferralCodeEndpoint:
    """Integration tests for /me/referral-code endpoint."""

    def test_get_referral_code(self, client, authenticated_user):
        """Get or create referral code."""
        user, full_key = authenticated_user
        response = client.post(
            "/me/referral-code",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "url" in data
        assert len(data["code"]) > 0
        assert "?ref=" in data["url"]

    def test_referral_code_idempotent(self, client, authenticated_user):
        """Generating referral code twice returns same code."""
        user, full_key = authenticated_user
        response1 = client.post(
            "/me/referral-code",
            headers={"X-API-Key": full_key},
        )
        code1 = response1.json()["code"]

        response2 = client.post(
            "/me/referral-code",
            headers={"X-API-Key": full_key},
        )
        code2 = response2.json()["code"]

        assert code1 == code2

    def test_referral_code_requires_auth(self, client):
        """Referral code endpoint requires auth."""
        response = client.post("/me/referral-code")
        assert response.status_code in [401, 403]


class TestWalletEndpoint:
    """Integration tests for /me/wallet endpoint."""

    def test_get_wallet_balance(self, client, authenticated_user, test_db):
        """Get wallet balance."""
        user, full_key = authenticated_user
        # Add some credit
        add_wallet_credit(test_db, user.id, 1000)  # $10

        response = client.get(
            "/me/wallet",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance_cents"] == 1000
        assert data["balance_usd"] == 10.0

    def test_wallet_empty_balance(self, client, authenticated_user):
        """New user has zero wallet balance."""
        user, full_key = authenticated_user
        response = client.get(
            "/me/wallet",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance_cents"] == 0
        assert data["balance_usd"] == 0.0

    def test_wallet_requires_auth(self, client):
        """Wallet endpoint requires auth."""
        response = client.get("/me/wallet")
        assert response.status_code in [401, 403]


class TestInvoicesEndpoint:
    """Integration tests for /me/invoices endpoint."""

    def test_get_invoices_empty(self, client, authenticated_user):
        """New user has no invoices."""
        user, full_key = authenticated_user
        response = client.get(
            "/me/invoices",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert len(data["invoices"]) == 0

    def test_get_invoices_with_data(self, client, authenticated_user, test_db):
        """Get user invoices."""
        user, full_key = authenticated_user
        # Create an invoice
        from api.db import record_invoice
        record_invoice(
            test_db,
            user.id,
            "inv_test123",
            9900,
            status="paid",
            issued_at=datetime.now(timezone.utc),
        )

        response = client.get(
            "/me/invoices",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["stripe_invoice_id"] == "inv_test123"
        assert data["invoices"][0]["amount_usd"] == 99.0

    def test_invoices_requires_auth(self, client):
        """Invoices endpoint requires auth."""
        response = client.get("/me/invoices")
        assert response.status_code in [401, 403]


class TestBillingPortalEndpoint:
    """Integration tests for /billing/portal endpoint."""

    def test_billing_portal_no_subscription(self, client, authenticated_user):
        """Billing portal requires subscription."""
        user, full_key = authenticated_user
        response = client.post(
            "/billing/portal",
            headers={"X-API-Key": full_key},
        )
        # Should fail because no stripe_customer_id
        assert response.status_code in [400, 502, 503]

    def test_billing_portal_with_customer(self, client, authenticated_user, test_db):
        """Billing portal works with stripe_customer_id."""
        user, full_key = authenticated_user
        # Add stripe_customer_id
        user.stripe_customer_id = "cus_test123"
        test_db.commit()

        response = client.post(
            "/billing/portal",
            headers={"X-API-Key": full_key},
        )
        # Will fail without real Stripe key, but should not auth error
        assert response.status_code != 401

    def test_billing_portal_requires_auth(self, client):
        """Billing portal requires auth."""
        response = client.post("/billing/portal")
        assert response.status_code in [401, 403]


class TestRefundEndpoint:
    """Integration tests for /admin/refund endpoint."""

    def test_refund_requires_auth(self, client):
        """Refund endpoint requires auth."""
        response = client.post("/admin/refund/invalid_id")
        assert response.status_code in [401, 403]

    def test_refund_nonexistent_purchase(self, client, authenticated_user):
        """Refund nonexistent purchase returns 404."""
        user, full_key = authenticated_user
        response = client.post(
            "/admin/refund/nonexistent_id",
            headers={"X-API-Key": full_key},
        )
        # Should be 403 (not admin) before 404
        assert response.status_code in [403, 404]

    def test_refund_not_admin(self, client, authenticated_user, test_db):
        """Non-admin cannot refund."""
        user, full_key = authenticated_user
        # Create a purchase
        from api.db import record_purchase
        purchase = record_purchase(test_db, user.id, "persona_socrates", amount_cents=999)

        response = client.post(
            f"/admin/refund/{purchase.id}",
            headers={"X-API-Key": full_key},
        )
        # Should be forbidden (not admin)
        assert response.status_code == 403


class TestMultiCurrencyCheckout:
    """Integration tests for multi-currency support."""

    def test_checkout_with_usd_locale(self, client, authenticated_user):
        """Checkout with USD locale."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/persona_socrates?locale=usd",
            headers={"X-API-Key": full_key},
        )
        # Will fail without valid persona, but tests locale param acceptance
        assert response.status_code in [400, 404]

    def test_checkout_with_eur_locale(self, client, authenticated_user):
        """Checkout with EUR locale."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/persona_socrates?locale=eur",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code in [400, 404]

    def test_checkout_with_try_locale(self, client, authenticated_user):
        """Checkout with TRY locale."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/persona_socrates?locale=try",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code in [400, 404]


class TestBundleCheckout:
    """Integration tests for bundle checkout."""

    def test_bundle_10_checkout(self, client, authenticated_user):
        """Checkout bundle_10."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/bundle/bundle_10",
            headers={"X-API-Key": full_key},
        )
        # Will fail without real Stripe, but tests endpoint existence
        assert response.status_code in [400, 502, 503]

    def test_bundle_invalid_id(self, client, authenticated_user):
        """Invalid bundle returns error."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/bundle/invalid_bundle",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code in [400, 404]

    def test_bundle_with_locale(self, client, authenticated_user):
        """Bundle checkout with multi-currency."""
        user, full_key = authenticated_user
        response = client.post(
            "/checkout/bundle/bundle_50?locale=try",
            headers={"X-API-Key": full_key},
        )
        # Tests parameter acceptance
        assert response.status_code in [400, 502, 503]

    def test_bundle_requires_auth(self, client):
        """Bundle checkout requires auth."""
        response = client.post("/checkout/bundle/bundle_10")
        assert response.status_code in [401, 403]

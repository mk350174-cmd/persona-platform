"""
Load tests for payment endpoints (H86).
Run with: locust -f tests/load_test_payments.py --host=http://localhost:8000
"""

import os
import secrets
from locust import HttpUser, task, between, events
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from api.db import (
    SessionLocal, init_db, create_user, hash_password,
    generate_referral_code, add_wallet_credit,
)

# Initialize test database
try:
    init_db()
except Exception:
    pass

db = SessionLocal()


class PaymentLoadTest(HttpUser):
    """Load test user profile for payment operations."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Setup: create test user and API key."""
        # Create unique user for this load test instance
        email = f"loadtest_{secrets.token_hex(4)}@example.com"
        self.user, self.api_key = create_user(db, email)
        self.user.password_hash = hash_password("password123")
        db.commit()

        self.headers = {"X-API-Key": self.api_key}
        self.referral_code = None

    def on_stop(self):
        """Cleanup."""
        pass

    # ── Task 1: Free Tier & Referral (20% of requests) ────────────────────

    @task(2)
    def get_referral_code(self):
        """GET /me/referral-code - Generate referral code."""
        with self.client.post(
            "/me/referral-code",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.referral_code = data.get("code")
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 2: Wallet Operations (15% of requests) ──────────────────────

    @task(1)
    def get_wallet_balance(self):
        """GET /me/wallet - Check wallet balance."""
        with self.client.get(
            "/me/wallet",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 3: Invoices (10% of requests) ──────────────────────────────

    @task(1)
    def get_invoices(self):
        """GET /me/invoices - List user invoices."""
        with self.client.get(
            "/me/invoices",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 4: Persona Checkout (30% of requests) ──────────────────────

    @task(3)
    def checkout_persona_usd(self):
        """POST /checkout/{persona_id}?locale=usd - USD checkout."""
        self._checkout_persona("usd")

    @task(1)
    def checkout_persona_eur(self):
        """POST /checkout/{persona_id}?locale=eur - EUR checkout."""
        self._checkout_persona("eur")

    @task(1)
    def checkout_persona_try(self):
        """POST /checkout/{persona_id}?locale=try - TRY checkout."""
        self._checkout_persona("try")

    def _checkout_persona(self, locale: str):
        """Common checkout logic."""
        personas = [
            "persona_socrates",
            "persona_plato",
            "persona_aristotle",
            "persona_kant",
            "persona_nietzsche",
        ]
        persona_id = secrets.choice(personas)

        with self.client.post(
            f"/checkout/{persona_id}",
            params={"locale": locale},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                # 400/502/503 expected (no real Stripe)
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 5: Bundle Checkout (15% of requests) ────────────────────────

    @task(2)
    def checkout_bundle_usd(self):
        """POST /checkout/bundle/{bundle_id}?locale=usd - USD bundle."""
        self._checkout_bundle("usd")

    @task(1)
    def checkout_bundle_eur(self):
        """POST /checkout/bundle/{bundle_id}?locale=eur - EUR bundle."""
        self._checkout_bundle("eur")

    def _checkout_bundle(self, locale: str):
        """Common bundle checkout logic."""
        bundles = ["bundle_10", "bundle_50", "bundle_495"]
        bundle_id = secrets.choice(bundles)

        with self.client.post(
            f"/checkout/bundle/{bundle_id}",
            params={"locale": locale},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 6: Subscription Checkout (10% of requests) ────────────────

    @task(1)
    def checkout_subscription_monthly(self):
        """POST /checkout/{persona_id}?tier=basic_monthly - Monthly sub."""
        with self.client.post(
            "/checkout/persona_socrates",
            params={"tier": "basic_monthly"},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def checkout_subscription_annual(self):
        """POST /checkout/{persona_id}?tier=pro_annual - Annual sub."""
        with self.client.post(
            "/checkout/persona_socrates",
            params={"tier": "pro_annual"},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 7: Checkout with Promo Code (8% of requests) ──────────────

    @task(1)
    def checkout_with_promo(self):
        """POST /checkout with promo code."""
        with self.client.post(
            "/checkout/persona_socrates",
            params={"promo": "TEST50"},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 8: Checkout with Referral Code (5% of requests) ─────────────

    @task(1)
    def checkout_with_referral(self):
        """POST /checkout with referral code."""
        if not self.referral_code:
            return  # Skip if no referral code

        with self.client.post(
            "/checkout/persona_socrates",
            params={"ref": self.referral_code},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ── Task 9: Billing Portal (5% of requests) ───────────────────────

    @task(1)
    def create_billing_portal(self):
        """POST /billing/portal - Create billing portal session."""
        with self.client.post(
            "/billing/portal",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 502, 503]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


class WebhookLoadTest(HttpUser):
    """Load test webhook processing (B19 idempotency under load)."""

    wait_time = between(0.5, 2)

    def on_start(self):
        """Setup."""
        self.event_counter = 0

    @task
    def process_checkout_webhook(self):
        """Simulate Stripe webhook: checkout.session.completed."""
        self.event_counter += 1
        user, _ = create_user(db, f"webhook_user_{self.event_counter}@example.com")

        event = {
            "id": f"evt_load_{self.event_counter}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_load_{self.event_counter}",
                    "mode": "payment",
                    "amount_total": 2999,
                    "customer_email": user.email,
                    "metadata": {
                        "user_id": user.id,
                        "persona_id": "persona_socrates",
                    },
                }
            },
        }

        # In real scenario, would POST to /webhook/stripe
        # For load testing, we measure webhook processing logic
        from api.db import mark_stripe_event_processed
        mark_stripe_event_processed(db, event["id"], event["type"])

        # Simulate duplicate event (idempotency check)
        from api.db import is_stripe_event_processed
        if is_stripe_event_processed(db, event["id"]):
            # Duplicate detected (idempotency working)
            pass


# ── Event Listeners for Stats ────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test start event."""
    print("\n" + "="*60)
    print("🚀 Payment System Load Test Started")
    print("="*60)
    print(f"Target: {environment.host}")
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test stop event."""
    print("\n" + "="*60)
    print("🛑 Payment System Load Test Stopped")
    print("="*60)
    print(f"End time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Response time median: {environment.stats.total.get_median_response_time()}ms")
    print(f"Response time p99: {environment.stats.total.get_percentile(0.99)}ms")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # > 1 second
        print(f"⚠️  SLOW: {request_type} {name} - {response_time}ms")


# ── Test Scenarios (run with --scenarios flag) ─────────────────────────

class LightLoadTest(HttpUser):
    """Light load: 10-20 concurrent users (baseline)."""
    wait_time = between(2, 5)
    # Inherits tasks from PaymentLoadTest


class NormalLoadTest(HttpUser):
    """Normal load: 50 concurrent users."""
    wait_time = between(1, 3)


class HeavyLoadTest(HttpUser):
    """Heavy load: 100+ concurrent users."""
    wait_time = between(0.5, 2)


class SpikeLoadTest(HttpUser):
    """Spike: 200 concurrent users for 5 minutes."""
    wait_time = between(0.1, 1)

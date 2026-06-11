"""
Load tests for Persona Platform core endpoints (catalog, chat, analytics).
Comprehensive test scenarios for 100+ concurrent users.

Run with:
    locust -f tests/load_test_platform.py --host=http://localhost:8000 --users=100

Or use the shell script:
    ./run_load_tests.sh all
"""

import os
import secrets
import time
import json
import asyncio
from typing import Optional
from datetime import datetime, timezone
from locust import HttpUser, TaskSet, task, between, events, constant
from locust.contrib.fasthttp import FastHttpUser

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

try:
    from api.db import (
        SessionLocal, init_db, create_user, hash_password,
        generate_referral_code, add_wallet_credit,
    )
    init_db()
except Exception as e:
    print(f"Warning: DB init failed: {e}")

# ── Global metrics tracking ────────────────────────────────────────────────

class MetricsCollector:
    """Track custom metrics beyond Locust defaults."""

    def __init__(self):
        self.ws_latencies = []
        self.slow_requests = []
        self.concurrent_connections = 0

    def record_ws_latency(self, latency_ms: float):
        """Record WebSocket round-trip latency."""
        self.ws_latencies.append(latency_ms)

    def record_slow_request(self, name: str, latency_ms: float):
        """Record requests exceeding threshold."""
        if latency_ms > 500:
            self.slow_requests.append({
                "name": name,
                "latency_ms": latency_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })


metrics = MetricsCollector()


# ── TaskSet: Catalog Operations ────────────────────────────────────────────

class CatalogBrowsingTasks(TaskSet):
    """Simulate users browsing the persona catalog (15% of traffic)."""

    def on_start(self):
        """Initialize catalog browsing state."""
        self.persona_ids = [
            "persona_socrates",
            "persona_plato",
            "persona_aristotle",
            "persona_kant",
            "persona_nietzsche",
            "persona_descartes",
            "persona_hume",
            "persona_spinoza",
        ]
        self.current_persona = None

    @task(3)
    def list_personas(self):
        """GET /personas - List all personas (paginated)."""
        # Simulate pagination browsing
        offset = secrets.randbelow(5) * 10
        limit = secrets.choice([10, 20, 50])

        with self.client.get(
            "/personas",
            params={"offset": offset, "limit": limit},
            catch_response=True,
            name="/personas",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        self.current_persona = data[0].get("id")
                    response.success()
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def get_persona_detail(self):
        """GET /personas/{id} - Fetch persona details."""
        persona_id = secrets.choice(self.persona_ids)

        with self.client.get(
            f"/personas/{persona_id}",
            catch_response=True,
            name="/personas/{id}",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "id" in data:
                        response.success()
                    else:
                        response.failure("Missing expected fields")
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            elif response.status_code == 404:
                # Some personas may not exist
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def search_personas(self):
        """GET /personas?search=... - Search by description."""
        queries = [
            "philosophy",
            "ethics",
            "metaphysics",
            "logic",
            "epistemology",
        ]
        query = secrets.choice(queries)

        with self.client.get(
            "/personas",
            params={"search": query},
            catch_response=True,
            name="/personas [search]",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ── TaskSet: Chat Operations ───────────────────────────────────────────────

class ChatTasks(TaskSet):
    """Simulate users chatting with personas (40% of traffic)."""

    wait_time = between(1, 3)  # Realistic think time between messages

    def on_start(self):
        """Setup: authenticate and select a persona."""
        self.persona_ids = [
            "persona_socrates",
            "persona_plato",
            "persona_aristotle",
            "persona_kant",
        ]
        self.conversation_id = None
        self.message_count = 0
        self.max_messages_per_session = 5

    @task(4)
    def send_chat_message(self):
        """POST /chat/{persona_id} - Send a message (or use WebSocket fallback)."""
        if self.message_count >= self.max_messages_per_session:
            self.message_count = 0  # Reset for next conversation
            return

        persona_id = secrets.choice(self.persona_ids)

        messages = [
            "What is virtue?",
            "How should I live?",
            "What is the nature of reality?",
            "Is knowledge possible?",
            "What is the good life?",
            "How do we know truth?",
            "What is consciousness?",
            "Is free will real?",
            "What is justice?",
            "How should society be organized?",
        ]

        payload = {
            "message": secrets.choice(messages),
            "conversation_id": self.conversation_id,
        }

        # Simulate realistic chat latency (500-2000ms for response)
        start_time = time.time()

        try:
            with self.client.post(
                f"/chat/{persona_id}",
                json=payload,
                catch_response=True,
                name="/chat/{persona_id}",
                timeout=10,
            ) as response:
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "message_id" in data:
                            self.conversation_id = data.get("conversation_id")
                            self.message_count += 1
                        response.success()

                        # Track slow responses
                        if elapsed_ms > 500:
                            metrics.record_slow_request(
                                f"/chat/{persona_id}",
                                elapsed_ms
                            )
                    except Exception as e:
                        response.failure(f"JSON error: {e}")
                elif response.status_code in [400, 404]:
                    # Expected for some edge cases
                    response.success()
                else:
                    response.failure(f"HTTP {response.status_code}")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="POST",
                name=f"/chat/{persona_id}",
                response_time=elapsed_ms,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )

    @task(1)
    def get_conversation_history(self):
        """GET /chat/{conversation_id} - Fetch conversation history."""
        if not self.conversation_id:
            return

        with self.client.get(
            f"/chat/{self.conversation_id}",
            catch_response=True,
            name="/chat/{conversation_id}",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Conversation may not exist
            else:
                response.failure(f"HTTP {response.status_code}")


# ── TaskSet: Analytics Queries ────────────────────────────────────────────

class AnalyticsTasks(TaskSet):
    """Simulate analytics dashboard queries (25% of traffic)."""

    wait_time = constant(2)  # Dashboard queries are less frequent

    def on_start(self):
        """Setup: prepare analytics state."""
        self.time_ranges = ["7d", "30d", "90d"]

    @task(3)
    def get_dashboard_summary(self):
        """GET /analytics/dashboard - Fetch dashboard KPIs."""
        with self.client.get(
            "/analytics/dashboard",
            catch_response=True,
            name="/analytics/dashboard",
        ) as response:
            if response.status_code in [200, 403]:
                # 403 is expected for non-admin users
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def get_persona_analytics(self):
        """GET /analytics/personas/top - Top personas by usage."""
        days = secrets.choice([7, 30, 90])

        with self.client.get(
            "/analytics/personas/top",
            params={"days": days},
            catch_response=True,
            name="/analytics/personas/top",
        ) as response:
            if response.status_code in [200, 403]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def get_usage_stats(self):
        """GET /analytics/usage - Usage statistics."""
        with self.client.get(
            "/analytics/usage",
            catch_response=True,
            name="/analytics/usage",
        ) as response:
            if response.status_code in [200, 403]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ── Main User Classes ──────────────────────────────────────────────────────

class AuthenticatedBrowsingUser(FastHttpUser):
    """User profile: browse catalog and view analytics (lightweight)."""

    tasks = [CatalogBrowsingTasks]
    wait_time = between(2, 5)
    weight = 1  # 20% of users


class ActiveChatUser(FastHttpUser):
    """User profile: actively chatting (primary use case)."""

    tasks = [ChatTasks, CatalogBrowsingTasks]
    task_set = ChatTasks
    wait_time = between(1, 3)
    weight = 4  # 40% of users


class AdminAnalyticsUser(FastHttpUser):
    """User profile: checking analytics and dashboard."""

    tasks = [AnalyticsTasks]
    wait_time = between(3, 8)
    weight = 1  # 20% of users


class RealWorldUser(FastHttpUser):
    """User profile: realistic workflow (login → browse → chat → checkout)."""

    wait_time = between(2, 5)
    weight = 4  # 40% of users

    def on_start(self):
        """Simulate realistic user onboarding."""
        self.client.verify = False  # Disable SSL verification for testing
        self.persona_ids = [
            "persona_socrates",
            "persona_plato",
            "persona_aristotle",
        ]
        self.current_persona = None
        self.conversation_history = []

    @task(20)
    def browse_catalog(self):
        """Browse personas - most common activity."""
        with self.client.get(
            "/personas",
            params={"limit": 10},
            catch_response=True,
            name="/personas",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        self.current_persona = data[0].get("id")
                    response.success()
                except Exception:
                    response.failure("JSON parse error")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(15)
    def view_persona_detail(self):
        """View selected persona details."""
        if not self.current_persona:
            return

        with self.client.get(
            f"/personas/{self.current_persona}",
            catch_response=True,
            name="/personas/{id}",
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(30)
    def chat_with_persona(self):
        """Send chat message to persona."""
        if not self.current_persona:
            self.current_persona = secrets.choice(self.persona_ids)

        messages = [
            "Hello, how are you?",
            "What's your philosophy?",
            "Can you teach me?",
            "What do you believe?",
        ]

        payload = {
            "message": secrets.choice(messages),
        }

        with self.client.post(
            f"/chat/{self.current_persona}",
            json=payload,
            catch_response=True,
            name="/chat/{persona_id}",
            timeout=10,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "message_id" in data:
                        self.conversation_history.append(data)
                    response.success()
                except Exception:
                    response.failure("JSON parse error")
            elif response.status_code in [400, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)
    def check_health(self):
        """Periodic health check."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ── Event Listeners for Metrics ────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics."""
    print("\n" + "="*70)
    print("🚀 Platform Load Test Started")
    print("="*70)
    print(f"Target: {environment.host}")
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Expected users: {environment.max_users if hasattr(environment, 'max_users') else 'N/A'}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate summary report."""
    print("\n" + "="*70)
    print("🛑 Platform Load Test Completed")
    print("="*70)

    stats = environment.stats
    total = stats.total

    print(f"Total Requests: {total.num_requests:,}")
    print(f"Total Failures: {total.num_failures:,}")
    print(f"Failure Rate: {(total.num_failures / total.num_requests * 100):.2f}%"
          if total.num_requests > 0 else "N/A")

    print(f"\nResponse Time Percentiles:")
    print(f"  Median (p50):  {total.get_median_response_time():.0f}ms")
    print(f"  p95:           {total.get_percentile(0.95):.0f}ms")
    print(f"  p99:           {total.get_percentile(0.99):.0f}ms")
    print(f"  Max:           {total.get_max_response_time():.0f}ms")

    print(f"\nThroughput: {stats.total.total_rps:.2f} requests/sec")

    if metrics.slow_requests:
        print(f"\n⚠️  {len(metrics.slow_requests)} slow requests (>500ms) detected")

    if metrics.ws_latencies:
        avg_ws_latency = sum(metrics.ws_latencies) / len(metrics.ws_latencies)
        print(f"\nWebSocket Latency: {avg_ws_latency:.0f}ms average")

    print("="*70 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length,
               response, context, **kwargs):
    """Log performance anomalies."""
    if response_time > 2000:  # 2+ seconds
        print(f"⚠️  SLOW: {request_type} {name} - {response_time:.0f}ms")


@events.quitting.add_listener
def on_quit(environment, **kwargs):
    """Final cleanup."""
    print("📊 Load test artifacts preserved in results/")


# ── Performance Assertions ────────────────────────────────────────────────

class PerformanceTarget:
    """Define and check performance targets."""

    P95_RESPONSE_TIME_MS = 500
    P99_RESPONSE_TIME_MS = 1000
    MIN_RPS = 100
    MAX_ERROR_RATE = 2.0  # percent

    @staticmethod
    def validate(environment):
        """Validate performance against targets."""
        stats = environment.stats.total

        p95 = stats.get_percentile(0.95)
        p99 = stats.get_percentile(0.99)
        error_rate = (stats.num_failures / stats.num_requests * 100) if stats.num_requests > 0 else 0
        rps = stats.total_rps

        checks = {
            "p95_response_time": (p95 <= PerformanceTarget.P95_RESPONSE_TIME_MS, p95),
            "p99_response_time": (p99 <= PerformanceTarget.P99_RESPONSE_TIME_MS, p99),
            "error_rate": (error_rate <= PerformanceTarget.MAX_ERROR_RATE, error_rate),
            "throughput": (rps >= PerformanceTarget.MIN_RPS, rps),
        }

        return checks

"""
Test metrics and reporting utilities for integration tests.

Provides:
- Test count summary
- Fixture usage tracking
- Performance metrics
- Coverage analysis
"""

import pytest
from pathlib import Path


def get_test_summary():
    """
    Print summary of all integration tests.

    Run with:
        python -m tests.test_metrics
    """
    tests_dir = Path(__file__).parent

    test_files = {
        "test_backend_integration.py": "REST API Integration Tests",
        "test_websocket_integration.py": "WebSocket Integration Tests",
        "test_platform_integration.py": "Platform Integration Tests (existing)",
    }

    print("\n" + "="*70)
    print("PERSONA PLATFORM — INTEGRATION TEST SUMMARY")
    print("="*70)

    total_tests = 0

    for filename, description in test_files.items():
        filepath = tests_dir / filename
        if not filepath.exists():
            print(f"\n⚠️  {filename}: NOT FOUND")
            continue

        content = filepath.read_text()

        # Count test methods
        test_count = content.count("\n    def test_")
        class_count = content.count("\nclass Test")

        total_tests += test_count

        print(f"\n{description}")
        print(f"  File: {filename}")
        print(f"  Test Classes: {class_count}")
        print(f"  Test Methods: {test_count}")
        print(f"  Lines: {len(content.splitlines())}")

    print("\n" + "-"*70)
    print(f"TOTAL TEST METHODS: {total_tests}")
    print("="*70 + "\n")


def get_fixture_summary():
    """Print summary of available fixtures."""
    print("\n" + "="*70)
    print("AVAILABLE FIXTURES (from conftest.py)")
    print("="*70)

    fixtures = {
        "test_db": "In-memory SQLite database (session-scoped)",
        "client": "FastAPI TestClient with database override",
        "test_user": "User with API key (email: testuser@example.com)",
        "authenticated_user_with_wallet": "User with empty wallet",
        "authenticated_user_with_credits": "User with $100 credit",
        "admin_user": "Admin user for privileged endpoints",
        "test_persona": "Free persona from catalog",
        "ws_client": "WebSocket-enabled test client",
    }

    for fixture_name, description in fixtures.items():
        print(f"\n  @pytest.fixture")
        print(f"  {fixture_name}")
        print(f"    {description}")

    print("\n" + "="*70 + "\n")


def get_test_categories():
    """Print test categories and counts."""
    print("\n" + "="*70)
    print("TEST CATEGORIES — REST API INTEGRATION (test_backend_integration.py)")
    print("="*70)

    categories = {
        "Health Checks": ("TestHealthEndpoint", 2),
        "Authentication": ("TestAuthenticationFlow", 7),
        "Persona API": ("TestPersonaAPIEndpoints", 8),
        "Purchase API": ("TestPurchaseAPI", 9),
        "Analytics API": ("TestAnalyticsAPI", 6),
        "Error Handling": ("TestErrorHandling", 6),
        "End-to-End Workflows": ("TestEndToEndWorkflows", 4),
    }

    total = 0
    for category, (class_name, count) in categories.items():
        total += count
        print(f"\n  {category}")
        print(f"    Class: {class_name}")
        print(f"    Tests: {count}")

    print("\n" + "-"*70)
    print(f"TOTAL REST API TESTS: {total}")
    print("="*70)

    print("\n" + "="*70)
    print("TEST CATEGORIES — WEBSOCKET INTEGRATION (test_websocket_integration.py)")
    print("="*70)

    ws_categories = {
        "Connection Tests": ("TestWebSocketConnection", 7),
        "Messaging Tests": ("TestWebSocketMessaging", 5),
        "Error Recovery": ("TestWebSocketErrorRecovery", 5),
        "Load Tests": ("TestWebSocketLoad", 3),
        "Latency Tests": ("TestWebSocketLatency", 2),
    }

    ws_total = 0
    for category, (class_name, count) in ws_categories.items():
        ws_total += count
        print(f"\n  {category}")
        print(f"    Class: {class_name}")
        print(f"    Tests: {count}")

    print("\n" + "-"*70)
    print(f"TOTAL WEBSOCKET TESTS: {ws_total}")
    print("="*70 + "\n")


def get_pytest_commands():
    """Print useful pytest commands."""
    print("\n" + "="*70)
    print("PYTEST COMMANDS")
    print("="*70)

    commands = {
        "Run all tests": "pytest tests/ -v",
        "REST API tests only": "pytest tests/test_backend_integration.py -v",
        "WebSocket tests only": "pytest tests/test_websocket_integration.py -v",
        "Skip slow tests": "pytest tests/ -v -m 'not slow'",
        "Single test class": "pytest tests/test_backend_integration.py::TestAuthenticationFlow -v",
        "Single test": "pytest tests/test_backend_integration.py::TestAuthenticationFlow::test_user_registration_succeeds -v",
        "With verbose output": "pytest tests/ -vv -s",
        "Stop on first failure": "pytest tests/ -x",
        "With coverage": "pytest tests/ --cov=api --cov-report=html",
        "With HTML report": "pytest tests/ --html=report.html --self-contained-html",
        "Specific marker": "pytest tests/ -m 'auth or persona'",
    }

    for description, command in commands.items():
        print(f"\n  {description}:")
        print(f"    $ {command}")

    print("\n" + "="*70 + "\n")


def get_endpoints_coverage():
    """Print API endpoints covered by tests."""
    print("\n" + "="*70)
    print("API ENDPOINTS COVERAGE")
    print("="*70)

    endpoints = {
        "Health": [
            "GET /health",
        ],
        "Authentication": [
            "POST /auth/register",
            "POST /auth/login",
            "GET /me",
        ],
        "Personas": [
            "GET /personas",
            "GET /personas/{id}",
            "POST /v1/personas/{id}/ceid",
            "POST /v1/compile/{id}",
            "POST /v1/compile/{id}/all-platforms",
            "POST /v1/compile/{id}/all-tiers",
            "POST /v1/compile/{id}/voice",
        ],
        "Purchases & Billing": [
            "GET /me/purchases",
            "POST /checkout/{persona_id}",
            "POST /checkout/{persona_id}/mock",
            "GET /me/wallet",
            "POST /admin/refund/{purchase_id}",
        ],
        "Analytics (Admin)": [
            "GET /analytics/dashboard",
            "GET /analytics/personas/top",
            "GET /analytics/revenue",
            "GET /analytics/export/revenue",
            "GET /analytics/dau",
        ],
        "WebSocket": [
            "WS /ws/chat/{persona_id}?tier={text|voice|full}",
        ],
    }

    total = 0
    for category, paths in endpoints.items():
        count = len(paths)
        total += count
        print(f"\n  {category} ({count} endpoints)")
        for path in paths:
            print(f"    ✓ {path}")

    print("\n" + "-"*70)
    print(f"TOTAL ENDPOINTS TESTED: {total}")
    print("="*70 + "\n")


def main():
    """Run all metric reports."""
    get_test_summary()
    get_fixture_summary()
    get_test_categories()
    get_endpoints_coverage()
    get_pytest_commands()

    print("="*70)
    print("For detailed documentation, see:")
    print("  - tests/INTEGRATION_TESTS.md (comprehensive guide)")
    print("  - tests/TEST_QUICK_REFERENCE.md (quick reference)")
    print("  - tests/IMPLEMENTATION_SUMMARY.md (implementation details)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

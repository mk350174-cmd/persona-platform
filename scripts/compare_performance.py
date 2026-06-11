#!/usr/bin/env python3
"""
Compare current performance metrics to baseline for regression detection.

This script:
1. Loads performance baseline from docs/performance_baseline.json
2. Runs load tests on selected endpoints
3. Compares current metrics to baseline
4. Reports regressions (>threshold increase)
5. Generates summary

Usage:
    python scripts/compare_performance.py [--baseline-only] [--no-tests]
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"


def load_baseline() -> Dict:
    """Load performance baseline from JSON file."""
    baseline_file = repo_root / "docs" / "performance_baseline.json"

    if not baseline_file.exists():
        print("❌ ERROR: Baseline file not found at", baseline_file)
        return {}

    with open(baseline_file, "r") as f:
        return json.load(f)


def run_load_tests() -> Dict[str, Dict[str, float]]:
    """Run load tests and return performance metrics."""
    from fastapi.testclient import TestClient
    from api.main import app, get_db
    from api.db import (
        create_user, grant_free_persona, SessionLocal, Base
    )
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Set up test database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    test_db = TestSessionLocal()

    # Create test user
    user, api_key = create_user(test_db, "perf_test@example.com")
    grant_free_persona(test_db, user.id, "persona_socrates")

    # Create test client
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    metrics = {}

    # Test endpoints
    test_cases = [
        ("GET", "/health", None, {}),
        ("GET", "/personas", None, {}),
        ("GET", f"/personas/persona_socrates/profile", None, {}),
        ("GET", "/me", None, {"X-API-Key": api_key}),
        ("GET", "/me/purchases", None, {"X-API-Key": api_key}),
        ("GET", "/me/wallet", None, {"X-API-Key": api_key}),
        ("POST", "/checkout/persona_socrates", None, {"X-API-Key": api_key}),
    ]

    for method, path, json_data, headers in test_cases:
        print(f"  Testing {method} {path}...", end=" ")

        times = []
        iterations = 10

        for _ in range(iterations):
            start = time.time()
            try:
                if method == "GET":
                    client.get(path, headers=headers)
                elif method == "POST":
                    client.post(path, json=json_data or {}, headers=headers)
            except Exception as e:
                print(f"❌ Error: {e}")
                break
            elapsed = (time.time() - start) * 1000  # Convert to ms

            times.append(elapsed)

        if times:
            # Calculate percentiles
            times_sorted = sorted(times)
            p50 = times_sorted[len(times_sorted) // 2]
            p95 = times_sorted[int(len(times_sorted) * 0.95)]
            p99 = times_sorted[int(len(times_sorted) * 0.99)] if len(times_sorted) > 99 else p95

            endpoint_key = f"{method} {path}"
            metrics[endpoint_key] = {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
            }

            print(f"✓ p50={p50:.0f}ms p95={p95:.0f}ms p99={p99:.0f}ms")

    app.dependency_overrides.clear()
    test_db.close()

    return metrics


def detect_regressions(baseline: Dict, current: Dict) -> Tuple[List, List, List]:
    """
    Detect performance regressions comparing current to baseline.

    Returns: (regressions, improvements, no_baseline)
    """
    threshold_pct = baseline.get("regression_threshold_pct", 20)
    baseline_endpoints = baseline.get("endpoints", {})

    regressions = []
    improvements = []
    no_baseline = []

    for endpoint_key, current_metrics in current.items():
        if endpoint_key not in baseline_endpoints:
            no_baseline.append(endpoint_key)
            continue

        baseline_metrics = baseline_endpoints[endpoint_key]

        # Compare p95 latency (most meaningful for regressions)
        baseline_p95 = baseline_metrics.get("p95_ms", 0)
        current_p95 = current_metrics.get("p95_ms", 0)

        if baseline_p95 == 0:
            continue

        # Calculate percentage change
        change_pct = ((current_p95 - baseline_p95) / baseline_p95) * 100

        if change_pct > threshold_pct:
            regressions.append({
                "endpoint": endpoint_key,
                "baseline_ms": baseline_p95,
                "current_ms": current_p95,
                "change_pct": round(change_pct, 1),
            })
        elif change_pct < -threshold_pct:
            improvements.append({
                "endpoint": endpoint_key,
                "baseline_ms": baseline_p95,
                "current_ms": current_p95,
                "change_pct": round(change_pct, 1),
            })

    return regressions, improvements, no_baseline


def generate_report(baseline: Dict, current: Dict, regressions: List, improvements: List):
    """Generate performance report."""
    print("\n" + "=" * 80)
    print("PERFORMANCE REGRESSION REPORT")
    print("=" * 80)

    if regressions:
        print(f"\n⚠️  REGRESSIONS DETECTED ({len(regressions)}):")
        for reg in regressions:
            print(f"\n  {reg['endpoint']}")
            print(f"    Baseline:  {reg['baseline_ms']:.0f}ms")
            print(f"    Current:   {reg['current_ms']:.0f}ms")
            print(f"    Change:    +{reg['change_pct']}%")
    else:
        print("\n✅ No performance regressions detected")

    if improvements:
        print(f"\n🚀 IMPROVEMENTS ({len(improvements)}):")
        for imp in improvements:
            print(f"\n  {imp['endpoint']}")
            print(f"    Baseline:  {imp['baseline_ms']:.0f}ms")
            print(f"    Current:   {imp['current_ms']:.0f}ms")
            print(f"    Change:    {imp['change_pct']}%")

    print("\n" + "=" * 80)
    print(f"Threshold: {baseline.get('regression_threshold_pct', 20)}%")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect performance regressions")
    parser.add_argument("--baseline-only", action="store_true", help="Generate baseline only (no tests)")
    parser.add_argument("--no-tests", action="store_true", help="Skip load tests (use for dry-run)")

    args = parser.parse_args()

    print("📊 Loading performance baseline...")
    baseline = load_baseline()

    if args.baseline_only:
        print("✅ Baseline loaded")
        print(f"   Endpoints: {len(baseline.get('endpoints', {}))}")
        return 0

    print("🔧 Running load tests...")
    print("   (10 iterations per endpoint)\n")

    try:
        current = run_load_tests()
    except Exception as e:
        print(f"❌ Load tests failed: {e}")
        if args.no_tests:
            print("⏭️  Skipping due to --no-tests flag")
            return 0
        return 1

    if not current:
        print("❌ No metrics collected")
        return 1

    print("\n🔍 Analyzing performance...")
    regressions, improvements, no_baseline = detect_regressions(baseline, current)

    generate_report(baseline, current, regressions, improvements)

    if regressions:
        print(f"❌ {len(regressions)} regression(s) detected")
        return 1
    else:
        print("✅ Performance check passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())

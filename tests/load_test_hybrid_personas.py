#!/usr/bin/env python3
"""
Load test for hybrid personas matching endpoint.

Tests concurrent requests to /api/v1/personas/match with:
- 50+ concurrent requests
- P99 latency measurement
- Cache hit rate tracking
- Performance report generation

Usage:
    pytest tests/load_test_hybrid_personas.py -v

    Or run directly:
    python tests/load_test_hybrid_personas.py --concurrency 50 --duration 60

Requirements:
    - pytest
    - requests
    - numpy
    - concurrent.futures (stdlib)
"""

import pytest
import requests
import time
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
from dataclasses import dataclass
import statistics
import argparse
import sys
from pathlib import Path

# Add repo root to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


@dataclass
class LoadTestMetrics:
    """Metrics from load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    latencies_ms: List[float]
    cache_hits: int
    cache_misses: int
    start_time: float
    end_time: float

    @property
    def mean_latency_ms(self) -> float:
        """Calculate mean latency."""
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def median_latency_ms(self) -> float:
        """Calculate median latency."""
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_latency_ms(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies_ms:
            return 0.0
        return np.percentile(self.latencies_ms, 95)

    @property
    def p99_latency_ms(self) -> float:
        """Calculate 99th percentile latency."""
        if not self.latencies_ms:
            return 0.0
        return np.percentile(self.latencies_ms, 99)

    @property
    def min_latency_ms(self) -> float:
        """Get minimum latency."""
        return min(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def max_latency_ms(self) -> float:
        """Get maximum latency."""
        return max(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total_cache_events = self.cache_hits + self.cache_misses
        if total_cache_events == 0:
            return 0.0
        return (self.cache_hits / total_cache_events) * 100

    @property
    def duration_seconds(self) -> float:
        """Calculate total test duration."""
        return self.end_time - self.start_time

    @property
    def requests_per_second(self) -> float:
        """Calculate requests per second throughput."""
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds


class HybridPersonasLoadTester:
    """Load tester for hybrid personas matching endpoint."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "test-key"):
        """Initialize load tester.

        Args:
            base_url: Base URL of API (default: localhost:8000)
            api_key: API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key
        self.match_endpoint = f"{base_url}/api/v1/personas/match"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def generate_random_k_layer(self, dimensions: int = 98) -> List[float]:
        """Generate random K-layer vector.

        Args:
            dimensions: Number of dimensions (default: 98)

        Returns:
            List of floats in range [0.2, 0.8]
        """
        return np.random.uniform(0.2, 0.8, dimensions).tolist()

    def single_request(self) -> Tuple[bool, float, Dict]:
        """Execute single matching request.

        Returns:
            Tuple of (success: bool, latency_ms: float, response_data: dict)
        """
        k_layer = self.generate_random_k_layer()
        payload = {"user_k_layer": k_layer}

        start = time.time()
        try:
            response = requests.post(
                self.match_endpoint,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            elapsed_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                return True, elapsed_ms, data
            else:
                return False, elapsed_ms, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return False, elapsed_ms, {"error": str(e)}

    def run_concurrent_load_test(
        self,
        num_requests: int = 50,
        concurrency: int = 10,
    ) -> LoadTestMetrics:
        """Run concurrent load test.

        Args:
            num_requests: Total number of requests to make
            concurrency: Number of concurrent threads

        Returns:
            LoadTestMetrics with results
        """
        metrics = LoadTestMetrics(
            total_requests=num_requests,
            successful_requests=0,
            failed_requests=0,
            latencies_ms=[],
            cache_hits=0,
            cache_misses=0,
            start_time=time.time(),
            end_time=0,
        )

        # Execute requests in thread pool
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(self.single_request)
                for _ in range(num_requests)
            ]

            for future in as_completed(futures):
                success, latency_ms, response = future.result()

                metrics.latencies_ms.append(latency_ms)

                if success:
                    metrics.successful_requests += 1
                    # Track cache stats if available
                    cache_stats = response.get("cache_stats", {})
                    if cache_stats:
                        metrics.cache_hits += cache_stats.get("hits", 0)
                        metrics.cache_misses += cache_stats.get("misses", 0)
                else:
                    metrics.failed_requests += 1

        metrics.end_time = time.time()
        return metrics

    def run_sustained_load_test(
        self,
        duration_seconds: int = 60,
        requests_per_second: float = 10.0,
    ) -> LoadTestMetrics:
        """Run sustained load test for fixed duration.

        Args:
            duration_seconds: How long to run test (seconds)
            requests_per_second: Target RPS

        Returns:
            LoadTestMetrics with results
        """
        metrics = LoadTestMetrics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            latencies_ms=[],
            cache_hits=0,
            cache_misses=0,
            start_time=time.time(),
            end_time=0,
        )

        interval = 1.0 / requests_per_second
        deadline = metrics.start_time + duration_seconds

        while time.time() < deadline:
            request_start = time.time()
            success, latency_ms, response = self.single_request()

            metrics.total_requests += 1
            metrics.latencies_ms.append(latency_ms)

            if success:
                metrics.successful_requests += 1
                cache_stats = response.get("cache_stats", {})
                if cache_stats:
                    metrics.cache_hits += cache_stats.get("hits", 0)
                    metrics.cache_misses += cache_stats.get("misses", 0)
            else:
                metrics.failed_requests += 1

            # Sleep to maintain target RPS
            elapsed = time.time() - request_start
            if elapsed < interval:
                time.sleep(interval - elapsed)

        metrics.end_time = time.time()
        return metrics

    def print_report(self, metrics: LoadTestMetrics):
        """Print formatted performance report.

        Args:
            metrics: LoadTestMetrics to report on
        """
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS — HYBRID PERSONAS MATCHING")
        print("=" * 80)

        print("\n📊 REQUEST METRICS")
        print("-" * 80)
        print(f"  Total Requests:        {metrics.total_requests}")
        print(f"  Successful:            {metrics.successful_requests} ({metrics.success_rate:.1f}%)")
        print(f"  Failed:                {metrics.failed_requests}")
        print(f"  Duration:              {metrics.duration_seconds:.1f}s")
        print(f"  Throughput:            {metrics.requests_per_second:.1f} req/sec")

        print("\n⏱️  LATENCY METRICS (milliseconds)")
        print("-" * 80)
        print(f"  Mean:                  {metrics.mean_latency_ms:.1f}ms")
        print(f"  Median:                {metrics.median_latency_ms:.1f}ms")
        print(f"  P95:                   {metrics.p95_latency_ms:.1f}ms")
        print(f"  P99:                   {metrics.p99_latency_ms:.1f}ms")
        print(f"  Min:                   {metrics.min_latency_ms:.1f}ms")
        print(f"  Max:                   {metrics.max_latency_ms:.1f}ms")

        print("\n💾 CACHE METRICS")
        print("-" * 80)
        print(f"  Cache Hits:            {metrics.cache_hits}")
        print(f"  Cache Misses:          {metrics.cache_misses}")
        print(f"  Hit Rate:              {metrics.cache_hit_rate:.1f}%")

        print("\n✅ BENCHMARKS")
        print("-" * 80)
        mean_target = 400.0
        p95_target = 600.0
        cache_target = 70.0

        mean_status = "✓ PASS" if metrics.mean_latency_ms < mean_target else "✗ FAIL"
        p95_status = "✓ PASS" if metrics.p95_latency_ms < p95_target else "✗ FAIL"
        success_status = "✓ PASS" if metrics.success_rate >= 99.0 else "✗ FAIL"
        cache_status = "✓ PASS" if metrics.cache_hit_rate >= cache_target else "⚠ BASELINE"

        print(f"  Mean Latency < {mean_target}ms:    {mean_status} ({metrics.mean_latency_ms:.1f}ms)")
        print(f"  P95 Latency < {p95_target}ms:   {p95_status} ({metrics.p95_latency_ms:.1f}ms)")
        print(f"  Success Rate >= 99%:       {success_status} ({metrics.success_rate:.1f}%)")
        print(f"  Cache Hit Rate >= {cache_target}%: {cache_status} ({metrics.cache_hit_rate:.1f}%)")

        print("\n" + "=" * 80)


# ──────────────────────────────────────────────────────────────────────
# Pytest Tests
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.load
class TestConcurrentLoad:
    """Load tests for concurrent persona matching."""

    @pytest.fixture
    def tester(self):
        """Create load tester instance."""
        return HybridPersonasLoadTester()

    def test_50_concurrent_requests(self, tester):
        """Test 50 concurrent requests to matching endpoint.

        Validates:
        - All requests complete
        - Success rate >= 95%
        - Mean latency < 400ms
        - P95 latency < 600ms
        """
        metrics = tester.run_concurrent_load_test(
            num_requests=50,
            concurrency=10,
        )

        tester.print_report(metrics)

        # Assertions
        assert metrics.total_requests == 50
        assert metrics.success_rate >= 95.0, f"Success rate {metrics.success_rate:.1f}% below 95%"
        assert metrics.mean_latency_ms < 400.0, f"Mean latency {metrics.mean_latency_ms:.1f}ms exceeds 400ms"
        assert metrics.p95_latency_ms < 600.0, f"P95 latency {metrics.p95_latency_ms:.1f}ms exceeds 600ms"

    def test_100_concurrent_requests(self, tester):
        """Test 100 concurrent requests to measure sustained load.

        Validates:
        - All requests complete
        - Success rate >= 90%
        - Mean latency < 500ms
        """
        metrics = tester.run_concurrent_load_test(
            num_requests=100,
            concurrency=20,
        )

        tester.print_report(metrics)

        assert metrics.total_requests == 100
        assert metrics.success_rate >= 90.0, f"Success rate {metrics.success_rate:.1f}% below 90%"
        assert metrics.mean_latency_ms < 500.0, f"Mean latency {metrics.mean_latency_ms:.1f}ms exceeds 500ms"

    def test_sustained_load_60_seconds(self, tester):
        """Test sustained load for 60 seconds at 10 RPS.

        Validates:
        - 600+ total requests completed (60s × 10 RPS)
        - Mean latency < 400ms
        - Cache hit rate baseline captured
        """
        metrics = tester.run_sustained_load_test(
            duration_seconds=60,
            requests_per_second=10.0,
        )

        tester.print_report(metrics)

        expected_requests = 60 * 10
        assert metrics.total_requests >= expected_requests * 0.9, \
            f"Only {metrics.total_requests} requests, expected ~{expected_requests}"
        assert metrics.mean_latency_ms < 400.0, \
            f"Mean latency {metrics.mean_latency_ms:.1f}ms exceeds 400ms"

    def test_burst_load(self, tester):
        """Test burst load: many requests in short time.

        Simulates burst traffic spike with 50 concurrent requests.
        """
        metrics = tester.run_concurrent_load_test(
            num_requests=50,
            concurrency=50,  # All at once
        )

        tester.print_report(metrics)

        assert metrics.total_requests == 50
        # More relaxed requirements for burst (higher latency expected)
        assert metrics.success_rate >= 90.0, f"Success rate {metrics.success_rate:.1f}% below 90%"


# ──────────────────────────────────────────────────────────────────────
# Standalone CLI Interface
# ──────────────────────────────────────────────────────────────────────

def main():
    """Run load test from command line."""
    parser = argparse.ArgumentParser(
        description="Load test for hybrid personas matching endpoint"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent threads (default: 10)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=50,
        help="Number of total requests (default: 50)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Run for N seconds at fixed RPS instead of fixed request count"
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=10.0,
        help="Requests per second for sustained load test (default: 10)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        default="test-key",
        help="API key for authentication (default: test-key)"
    )

    args = parser.parse_args()

    tester = HybridPersonasLoadTester(
        base_url=args.base_url,
        api_key=args.api_key,
    )

    if args.duration:
        # Sustained load test
        print(f"\n🚀 Starting sustained load test: {args.duration}s at {args.rps} RPS\n")
        metrics = tester.run_sustained_load_test(
            duration_seconds=args.duration,
            requests_per_second=args.rps,
        )
    else:
        # Concurrent load test
        print(f"\n🚀 Starting concurrent load test: {args.requests} requests, {args.concurrency} concurrent\n")
        metrics = tester.run_concurrent_load_test(
            num_requests=args.requests,
            concurrency=args.concurrency,
        )

    tester.print_report(metrics)

    # Exit with appropriate code
    if metrics.success_rate < 95.0:
        sys.exit(1)
    if metrics.mean_latency_ms > 400.0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Compare load test results across runs.
Useful for detecting performance regressions.

Usage:
    python scripts/compare_load_tests.py \
      --baseline results/baseline.json \
      --current results/test_run.json \
      --threshold 10

    # Or compare two CSV files
    python scripts/compare_load_tests.py \
      --baseline-csv results/baseline_stats.csv \
      --current-csv results/current_stats.csv
"""

import json
import csv
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class TestMetrics:
    """Container for test metrics."""
    requests: int
    failures: int
    error_rate: float
    rps: float
    p50: float
    p95: float
    p99: float
    max_time: float

    def to_dict(self) -> Dict:
        return {
            'requests': self.requests,
            'failures': self.failures,
            'error_rate': self.error_rate,
            'rps': self.rps,
            'p50': self.p50,
            'p95': self.p95,
            'p99': self.p99,
            'max_time': self.max_time,
        }

    def save_json(self, filepath: str):
        """Save metrics to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def from_json(filepath: str) -> 'TestMetrics':
        """Load metrics from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return TestMetrics(**data)

    @staticmethod
    def from_csv(filepath: str) -> 'TestMetrics':
        """Parse metrics from Locust stats CSV."""
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Name') == 'Aggregated':
                    requests = int(row.get('Number of requests', 0))
                    failures = int(row.get('Number of failures', 0))
                    error_rate = (failures / requests * 100) if requests > 0 else 0

                    return TestMetrics(
                        requests=requests,
                        failures=failures,
                        error_rate=error_rate,
                        rps=requests / 600,  # Assume 10-minute test
                        p50=float(row.get('Median response time', 0)),
                        p95=float(row.get('95th percentile', 0)),
                        p99=float(row.get('99th percentile', 0)),
                        max_time=float(row.get('Max response time', 0)),
                    )

        raise ValueError("No 'Aggregated' row found in CSV")


class MetricsComparator:
    """Compare two sets of metrics and detect regressions."""

    def __init__(self, threshold_pct: float = 10):
        """Initialize with regression threshold (percentage)."""
        self.threshold_pct = threshold_pct
        self.results = []

    def compare(self, baseline: TestMetrics, current: TestMetrics) -> Dict:
        """Compare metrics and return detailed results."""
        results = {
            'pass': True,
            'metrics': {},
        }

        # Check each metric
        checks = [
            ('Error Rate', baseline.error_rate, current.error_rate, 'lower'),
            ('Throughput (RPS)', baseline.rps, current.rps, 'higher'),
            ('p50 Response Time', baseline.p50, current.p50, 'lower'),
            ('p95 Response Time', baseline.p95, current.p95, 'lower'),
            ('p99 Response Time', baseline.p99, current.p99, 'lower'),
            ('Max Response Time', baseline.max_time, current.max_time, 'lower'),
        ]

        for metric_name, baseline_val, current_val, direction in checks:
            pct_change = self._calculate_change(baseline_val, current_val)
            is_regression = self._is_regression(
                baseline_val, current_val, direction, pct_change
            )

            metric_result = {
                'baseline': baseline_val,
                'current': current_val,
                'change_pct': pct_change,
                'is_regression': is_regression,
                'direction': direction,
            }

            results['metrics'][metric_name] = metric_result

            if is_regression:
                results['pass'] = False

        return results

    def _calculate_change(self, baseline: float, current: float) -> float:
        """Calculate percentage change."""
        if baseline == 0:
            return 0
        return ((current - baseline) / baseline) * 100

    def _is_regression(
        self,
        baseline: float,
        current: float,
        direction: str,
        pct_change: float,
    ) -> bool:
        """Determine if change is a regression."""
        if direction == 'higher':
            # Higher is better (RPS)
            return pct_change < -self.threshold_pct
        else:
            # Lower is better (latency, errors)
            return pct_change > self.threshold_pct

    def print_results(self, results: Dict, detailed: bool = False):
        """Print comparison results."""
        print("\n" + "="*70)
        print("📊 Load Test Comparison Report")
        print("="*70)

        if results['pass']:
            print("✅ PASS - No significant regressions detected\n")
        else:
            print("❌ FAIL - Performance regressions detected\n")

        # Print metric details
        print(f"{'Metric':<30} {'Baseline':>12} {'Current':>12} {'Change':>12}")
        print("-"*70)

        for metric_name, metric_result in results['metrics'].items():
            baseline = metric_result['baseline']
            current = metric_result['current']
            pct_change = metric_result['change_pct']
            is_regression = metric_result['is_regression']

            status = "⚠️" if is_regression else "✅"
            sign = "+" if pct_change > 0 else ""

            print(
                f"{metric_name:<30} {baseline:>12.1f} {current:>12.1f} "
                f"{status} {sign}{pct_change:>9.1f}%"
            )

        if detailed:
            print("\n" + "-"*70)
            print("Detailed Breakdown:\n")
            for metric_name, metric_result in results['metrics'].items():
                if metric_result['is_regression']:
                    print(f"⚠️  {metric_name}")
                    print(
                        f"   Baseline: {metric_result['baseline']:.1f} → "
                        f"Current: {metric_result['current']:.1f} "
                        f"({metric_result['change_pct']:+.1f}%)"
                    )
                    print(f"   Expected: {metric_result['direction']} is better")
                    print()

        print("="*70 + "\n")

        return results['pass']


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare load test results and detect regressions'
    )

    parser.add_argument(
        '--baseline',
        help='Baseline metrics JSON file',
        type=str,
    )
    parser.add_argument(
        '--baseline-csv',
        help='Baseline Locust stats CSV file',
        type=str,
    )
    parser.add_argument(
        '--current',
        help='Current test metrics JSON file',
        type=str,
    )
    parser.add_argument(
        '--current-csv',
        help='Current test Locust stats CSV file',
        type=str,
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=10,
        help='Regression threshold percentage (default: 10%%)',
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Print detailed breakdown',
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save results to JSON file',
    )

    args = parser.parse_args()

    # Load baseline metrics
    if args.baseline:
        baseline_metrics = TestMetrics.from_json(args.baseline)
    elif args.baseline_csv:
        baseline_metrics = TestMetrics.from_csv(args.baseline_csv)
    else:
        print("❌ Error: Must specify --baseline or --baseline-csv")
        sys.exit(1)

    # Load current metrics
    if args.current:
        current_metrics = TestMetrics.from_json(args.current)
    elif args.current_csv:
        current_metrics = TestMetrics.from_csv(args.current_csv)
    else:
        print("❌ Error: Must specify --current or --current-csv")
        sys.exit(1)

    # Compare
    comparator = MetricsComparator(threshold_pct=args.threshold)
    results = comparator.compare(baseline_metrics, current_metrics)

    # Print results
    passed = comparator.print_results(results, detailed=args.detailed)

    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}\n")

    # Exit with status code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()

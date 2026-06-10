"""
Analyze and compare load test results (H86).
Parses Locust CSV output and generates performance report.

Usage:
    python tests/analyze_load_results.py results/
"""

import os
import csv
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime


@dataclass
class LoadTestMetrics:
    """Container for load test metrics."""
    scenario: str
    num_requests: int
    num_failures: int
    total_time: float
    rps: float
    response_time_median: float
    response_time_p95: float
    response_time_p99: float
    response_time_max: float
    error_rate: float

    def __str__(self) -> str:
        """Format as readable string."""
        return f"""
{self.scenario} Results
{'='*50}
Requests: {self.num_requests} | Failures: {self.num_failures}
Error Rate: {self.error_rate:.2f}%
RPS: {self.rps:.2f} requests/sec
Response Times:
  - Median: {self.response_time_median:.0f}ms
  - p95:    {self.response_time_p95:.0f}ms
  - p99:    {self.response_time_p99:.0f}ms
  - Max:    {self.response_time_max:.0f}ms
"""


class LoadTestAnalyzer:
    """Analyze load test results."""

    def __init__(self, results_dir: str = "results"):
        """Initialize analyzer."""
        self.results_dir = Path(results_dir)
        self.metrics: Dict[str, LoadTestMetrics] = {}

    def parse_locust_stats(self, csv_file: str) -> Dict:
        """Parse Locust stats CSV file."""
        stats = {}
        response_times = []

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Name') == 'Aggregated':
                    stats = {
                        'requests': int(row['Number of requests']),
                        'failures': int(row['Number of failures']),
                        'median': float(row['Median response time']),
                        'p95': float(row['95th percentile']),
                        'p99': float(row['99th percentile']),
                        'max': float(row['Max response time']),
                    }
        return stats

    def analyze_scenario(self, scenario_name: str, csv_file: str,
                        duration_minutes: float) -> LoadTestMetrics:
        """Analyze a load test scenario."""
        stats = self.parse_locust_stats(csv_file)

        num_requests = stats.get('requests', 0)
        num_failures = stats.get('failures', 0)
        error_rate = (num_failures / num_requests * 100) if num_requests > 0 else 0
        rps = num_requests / (duration_minutes * 60) if duration_minutes > 0 else 0

        metrics = LoadTestMetrics(
            scenario=scenario_name,
            num_requests=num_requests,
            num_failures=num_failures,
            total_time=duration_minutes * 60,
            rps=rps,
            response_time_median=stats.get('median', 0),
            response_time_p95=stats.get('p95', 0),
            response_time_p99=stats.get('p99', 0),
            response_time_max=stats.get('max', 0),
            error_rate=error_rate,
        )

        return metrics

    def load_all_results(self) -> None:
        """Load all result files from results directory."""
        scenarios = {
            'light_load': ('results/light_load_stats.csv', 5),
            'normal_load': ('results/normal_load_stats.csv', 10),
            'heavy_load': ('results/heavy_load_stats.csv', 10),
            'spike_load': ('results/spike_load_stats.csv', 5),
        }

        for scenario_name, (csv_file, duration) in scenarios.items():
            path = Path(csv_file)
            if path.exists():
                metrics = self.analyze_scenario(scenario_name, csv_file, duration)
                self.metrics[scenario_name] = metrics
                print(metrics)

    def generate_report(self) -> str:
        """Generate comprehensive load test report."""
        report = f"""
PAYMENT SYSTEM LOAD TEST REPORT
Generated: {datetime.now().isoformat()}
{'='*70}

EXECUTIVE SUMMARY
{'-'*70}
"""

        # Overall stats
        total_requests = sum(m.num_requests for m in self.metrics.values())
        total_failures = sum(m.num_failures for m in self.metrics.values())
        avg_error_rate = statistics.mean(
            [m.error_rate for m in self.metrics.values() if m.num_requests > 0]
        ) if self.metrics else 0

        report += f"""
Total Requests: {total_requests:,}
Total Failures: {total_failures:,}
Average Error Rate: {avg_error_rate:.2f}%
Test Scenarios: {len(self.metrics)}

SCENARIO RESULTS
{'-'*70}
"""

        # Add each scenario
        for name, metrics in self.metrics.items():
            report += f"\n{metrics}\n"

        # Performance analysis
        report += f"""
PERFORMANCE ANALYSIS
{'-'*70}

Response Time Trends:
"""

        if 'light_load' in self.metrics and 'normal_load' in self.metrics:
            light_p95 = self.metrics['light_load'].response_time_p95
            normal_p95 = self.metrics['normal_load'].response_time_p95
            increase = ((normal_p95 - light_p95) / light_p95 * 100) if light_p95 > 0 else 0
            report += f"  Light → Normal: {increase:+.1f}% change in p95\n"

        if 'normal_load' in self.metrics and 'heavy_load' in self.metrics:
            normal_p95 = self.metrics['normal_load'].response_time_p95
            heavy_p95 = self.metrics['heavy_load'].response_time_p95
            increase = ((heavy_p95 - normal_p95) / normal_p95 * 100) if normal_p95 > 0 else 0
            report += f"  Normal → Heavy: {increase:+.1f}% change in p95\n"

        # Recommendations
        report += f"""
RECOMMENDATIONS
{'-'*70}
"""

        max_error_rate = max(
            (m.error_rate for m in self.metrics.values()),
            default=0
        )

        if max_error_rate > 5:
            report += "⚠️  HIGH ERROR RATE DETECTED\n"
            report += "  - Check database connection limits\n"
            report += "  - Review rate limiting thresholds\n"
            report += "  - Increase connection pool size\n"
        elif max_error_rate > 2:
            report += "⚠️  ELEVATED ERROR RATE\n"
            report += "  - Monitor for patterns in errors\n"
            report += "  - Consider gradual scaling\n"
        else:
            report += "✅ Error rates are acceptable\n"

        # Response time analysis
        max_p99 = max(
            (m.response_time_p99 for m in self.metrics.values()),
            default=0
        )

        if max_p99 > 5000:
            report += f"\n⚠️  SLOW RESPONSE TIMES (p99 > 5s)\n"
            report += "  - Add database indexes\n"
            report += "  - Profile slow queries\n"
            report += "  - Increase server resources\n"
        elif max_p99 > 2000:
            report += f"\n⚠️  ELEVATED RESPONSE TIMES (p99 > 2s)\n"
            report += "  - Review query performance\n"
            report += "  - Consider caching\n"
        else:
            report += f"\n✅ Response times are acceptable (p99 < {max_p99:.0f}ms)\n"

        # Throughput analysis
        throughputs = [m.rps for m in self.metrics.values() if m.rps > 0]
        if throughputs:
            max_rps = max(throughputs)
            if max_rps < 100:
                report += f"\n⚠️  LOW THROUGHPUT ({max_rps:.0f} RPS max)\n"
                report += "  - System may not handle production traffic\n"
                report += "  - Consider optimization or scaling\n"
            elif max_rps < 300:
                report += f"\n✅ Moderate throughput ({max_rps:.0f} RPS max)\n"
            else:
                report += f"\n✅ Good throughput ({max_rps:.0f} RPS max)\n"

        report += f"""
NEXT STEPS
{'-'*70}
1. Review and address any warnings above
2. Run targeted tests for failing scenarios
3. Implement database optimizations if needed
4. Set up continuous monitoring for regression detection
5. Schedule regular load tests in CI/CD pipeline

"""

        return report

    def save_report(self, filename: str = "load_test_report.txt") -> None:
        """Save report to file."""
        report = self.generate_report()
        with open(filename, 'w') as f:
            f.write(report)
        print(f"Report saved to {filename}")


def main():
    """Main entry point."""
    import sys

    results_dir = sys.argv[1] if len(sys.argv) > 1 else "results"

    analyzer = LoadTestAnalyzer(results_dir)

    print("📊 Load Test Results Analyzer")
    print(f"Results directory: {results_dir}")
    print()

    # Attempt to load results
    try:
        analyzer.load_all_results()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure to run Locust with --csv flag first:")
        print("  locust -f tests/load_test_payments.py --host=http://localhost:8000 --csv=results/light_load")
        return

    # Generate and save report
    report = analyzer.generate_report()
    print(report)

    # Save report
    analyzer.save_report("load_test_report.txt")
    print("✅ Analysis complete!")


if __name__ == "__main__":
    main()

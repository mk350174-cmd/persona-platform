#!/usr/bin/env python3
"""
Baseline Metrics Analyzer — Compare current load test results against baseline expectations.

Features:
- Define baseline expectations (p95, p99, RPS, error rate)
- Compare current vs baseline with regression detection
- Generate HTML reports with performance charts
- Alert on metric violations
- Support for multiple test scenarios

Usage:
    python tests/baseline_metrics.py --current results/normal_baseline_20260611_150000_metrics.json
    python tests/baseline_metrics.py --current current.json --baseline results/baselines/baseline.json
    python tests/baseline_metrics.py --check-alerts metrics.json --output alerts.json
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import math


# ════════════════════════════════════════════════════════════════════════════
# Baseline Definitions
# ════════════════════════════════════════════════════════════════════════════

class BaselineDefinitions:
    """Define expected baseline metrics for different scenarios."""

    SCENARIOS = {
        'normal': {
            'users': 50,
            'duration_minutes': 10,
            'description': 'Normal production load (50 users)',
            'metrics': {
                'p50_ms': {'target': 200, 'acceptable_variance': 0.20},
                'p95_ms': {'target': 500, 'acceptable_variance': 0.20},
                'p99_ms': {'target': 1000, 'acceptable_variance': 0.20},
                'error_rate_pct': {'target': 0.5, 'acceptable_variance': 0.50},
                'rps': {'target': 20, 'acceptable_variance': 0.30},
            }
        },
        'light': {
            'users': 20,
            'duration_minutes': 5,
            'description': 'Light load baseline (20 users)',
            'metrics': {
                'p50_ms': {'target': 150, 'acceptable_variance': 0.20},
                'p95_ms': {'target': 350, 'acceptable_variance': 0.20},
                'p99_ms': {'target': 700, 'acceptable_variance': 0.20},
                'error_rate_pct': {'target': 0.5, 'acceptable_variance': 0.50},
                'rps': {'target': 10, 'acceptable_variance': 0.30},
            }
        },
        'heavy': {
            'users': 100,
            'duration_minutes': 10,
            'description': 'Heavy load test (100 users)',
            'metrics': {
                'p50_ms': {'target': 300, 'acceptable_variance': 0.20},
                'p95_ms': {'target': 800, 'acceptable_variance': 0.20},
                'p99_ms': {'target': 1500, 'acceptable_variance': 0.20},
                'error_rate_pct': {'target': 1.0, 'acceptable_variance': 1.00},
                'rps': {'target': 50, 'acceptable_variance': 0.30},
            }
        },
        'spike': {
            'users': 200,
            'duration_minutes': 5,
            'description': 'Spike load test (200 users)',
            'metrics': {
                'p50_ms': {'target': 500, 'acceptable_variance': 0.30},
                'p95_ms': {'target': 1200, 'acceptable_variance': 0.30},
                'p99_ms': {'target': 2000, 'acceptable_variance': 0.30},
                'error_rate_pct': {'target': 2.0, 'acceptable_variance': 1.50},
                'rps': {'target': 100, 'acceptable_variance': 0.40},
            }
        }
    }

    # Alert thresholds (trigger investigation)
    ALERT_THRESHOLDS = {
        'p95_regression_pct': 15,      # Alert if >15% slower than baseline
        'error_rate_increase': 2.0,    # Alert if error rate increases by >2%
        'rps_decrease_pct': 20,        # Alert if throughput drops >20%
    }


# ════════════════════════════════════════════════════════════════════════════
# Metrics Comparison
# ════════════════════════════════════════════════════════════════════════════

class MetricsComparator:
    """Compare metrics against baseline expectations."""

    def __init__(self, baseline_defs: BaselineDefinitions = None):
        self.baseline_defs = baseline_defs or BaselineDefinitions()

    def compare_metric(
        self,
        metric_name: str,
        current_value: float,
        target_value: float,
        variance_allowed: float
    ) -> Tuple[str, float]:
        """
        Compare metric against target with allowed variance.

        Returns:
            Tuple of (status, variance_pct) where status is "pass", "warn", or "fail"
        """
        if target_value == 0:
            return "pass", 0.0

        variance_pct = ((current_value - target_value) / target_value) * 100
        max_variance_pct = variance_allowed * 100

        if abs(variance_pct) <= max_variance_pct:
            return "pass", variance_pct
        elif abs(variance_pct) <= max_variance_pct * 2:
            return "warn", variance_pct
        else:
            return "fail", variance_pct

    def compare_to_baseline(
        self,
        current: Dict,
        baseline: Dict,
        scenario: str = 'normal'
    ) -> Dict:
        """
        Compare current metrics to baseline.

        Returns dict with comparison results for each metric.
        """
        results = {
            'scenario': scenario,
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'summary': {
                'passed': 0,
                'warnings': 0,
                'failures': 0,
            }
        }

        baseline_metrics = self.baseline_defs.SCENARIOS[scenario]['metrics']

        for metric_name, expected in baseline_metrics.items():
            if metric_name not in current:
                continue

            current_value = current[metric_name]
            baseline_value = baseline.get(metric_name, expected['target'])

            # For regression detection, compare against previous baseline
            # not the target
            status, variance = self.compare_metric(
                metric_name,
                current_value,
                baseline_value,
                expected['acceptable_variance']
            )

            results['metrics'][metric_name] = {
                'current': current_value,
                'baseline': baseline_value,
                'target': expected['target'],
                'variance_pct': variance,
                'status': status,
            }

            results['summary'][status + 's'] += 1

        return results

    def check_alerts(self, current: Dict, baseline: Dict = None) -> List[Dict]:
        """Check for performance alerts."""
        alerts = []

        if baseline is None:
            return alerts

        alert_config = self.baseline_defs.ALERT_THRESHOLDS

        # Check p95 regression
        if 'p95_ms' in current and 'p95_ms' in baseline:
            p95_regression = ((current['p95_ms'] - baseline['p95_ms']) / baseline['p95_ms']) * 100
            if p95_regression > alert_config['p95_regression_pct']:
                alerts.append({
                    'severity': 'high',
                    'metric': 'p95_response_time',
                    'message': f"p95 response time increased {p95_regression:.1f}% (baseline: {baseline['p95_ms']:.0f}ms, current: {current['p95_ms']:.0f}ms)",
                })

        # Check error rate increase
        if 'error_rate_pct' in current and 'error_rate_pct' in baseline:
            error_increase = current['error_rate_pct'] - baseline['error_rate_pct']
            if error_increase > alert_config['error_rate_increase']:
                alerts.append({
                    'severity': 'high',
                    'metric': 'error_rate',
                    'message': f"Error rate increased {error_increase:.2f}% (baseline: {baseline['error_rate_pct']:.2f}%, current: {current['error_rate_pct']:.2f}%)",
                })

        # Check RPS decrease
        if 'rps' in current and 'rps' in baseline:
            rps_decrease = ((baseline['rps'] - current['rps']) / baseline['rps']) * 100
            if rps_decrease > alert_config['rps_decrease_pct']:
                alerts.append({
                    'severity': 'medium',
                    'metric': 'throughput',
                    'message': f"Throughput decreased {rps_decrease:.1f}% (baseline: {baseline['rps']:.1f} RPS, current: {current['rps']:.1f} RPS)",
                })

        return alerts


# ════════════════════════════════════════════════════════════════════════════
# HTML Report Generation
# ════════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Generate HTML reports from comparison results."""

    @staticmethod
    def generate_html_report(
        comparison: Dict,
        output_path: str,
        alerts: List[Dict] = None
    ) -> None:
        """Generate an HTML report from comparison results."""
        alerts = alerts or []

        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test Baseline Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1a1a1a;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }
        h2 {
            color: #333;
            margin-top: 30px;
            border-left: 4px solid #0066cc;
            padding-left: 15px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #999;
        }
        .stat-card.pass {
            border-left-color: #28a745;
        }
        .stat-card.warn {
            border-left-color: #ffc107;
        }
        .stat-card.fail {
            border-left-color: #dc3545;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        thead {
            background: #f0f0f0;
        }
        th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-pass {
            background: #d4edda;
            color: #155724;
        }
        .status-warn {
            background: #fff3cd;
            color: #856404;
        }
        .status-fail {
            background: #f8d7da;
            color: #721c24;
        }
        .variance-positive {
            color: #dc3545;
        }
        .variance-negative {
            color: #28a745;
        }
        .alerts {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
        }
        .alert-item {
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
        }
        .alert-high {
            border-left-color: #dc3545;
        }
        .timestamp {
            color: #666;
            font-size: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
        }
        .metric-name {
            font-weight: 600;
            margin-bottom: 10px;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            font-size: 14px;
        }
        .metric-label {
            color: #666;
        }
        .metric-value {
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Load Test Baseline Report</h1>
"""

        # Add timestamp
        html += f'<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>\n'

        # Add alerts if any
        if alerts:
            html += '<div class="alerts">\n'
            html += '<h3>⚠️ Performance Alerts</h3>\n'
            for alert in alerts:
                severity = alert.get('severity', 'medium')
                html += f'<div class="alert-item alert-{severity}">\n'
                html += f'<strong>{alert["metric"].upper()}:</strong> {alert["message"]}\n'
                html += '</div>\n'
            html += '</div>\n'

        # Summary section
        html += '<h2>Summary</h2>\n'
        html += '<div class="summary">\n'
        summary = comparison['summary']
        html += f'<div class="stat-card pass"><div class="stat-label">Passed</div><div class="stat-value">{summary["passed"]}</div></div>\n'
        html += f'<div class="stat-card warn"><div class="stat-label">Warnings</div><div class="stat-value">{summary["warnings"]}</div></div>\n'
        html += f'<div class="stat-card fail"><div class="stat-label">Failures</div><div class="stat-value">{summary["failures"]}</div></div>\n'
        html += '</div>\n'

        # Metrics table
        html += '<h2>Metric Comparison</h2>\n'
        html += '<table>\n'
        html += '<thead>\n'
        html += '<tr><th>Metric</th><th>Current</th><th>Baseline</th><th>Target</th><th>Variance</th><th>Status</th></tr>\n'
        html += '</thead>\n'
        html += '<tbody>\n'

        for metric_name, result in comparison['metrics'].items():
            status = result['status']
            variance = result['variance_pct']
            variance_class = 'variance-positive' if variance > 0 else 'variance-negative'

            html += f'<tr>\n'
            html += f'<td><strong>{metric_name}</strong></td>\n'
            html += f'<td>{result["current"]:.2f}</td>\n'
            html += f'<td>{result["baseline"]:.2f}</td>\n'
            html += f'<td>{result["target"]:.2f}</td>\n'
            html += f'<td><span class="{variance_class}">{variance:+.1f}%</span></td>\n'
            html += f'<td><span class="status-badge status-{status}">{status.upper()}</span></td>\n'
            html += f'</tr>\n'

        html += '</tbody>\n'
        html += '</table>\n'

        html += '<div class="timestamp">Report generated: ' + datetime.now().isoformat() + '</div>\n'
        html += '</div>\n'
        html += '</body>\n'
        html += '</html>\n'

        with open(output_path, 'w') as f:
            f.write(html)


# ════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Analyze load test metrics against baseline expectations'
    )
    parser.add_argument('--current', required=False, help='Current metrics JSON file')
    parser.add_argument('--baseline', help='Previous baseline JSON file')
    parser.add_argument('--scenario', default='normal', help='Test scenario (normal, light, heavy, spike)')
    parser.add_argument('--output', help='Output HTML report path')
    parser.add_argument('--check-alerts', help='Check alerts for given metrics file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    baseline_defs = BaselineDefinitions()
    comparator = MetricsComparator(baseline_defs)
    report_gen = ReportGenerator()

    # Handle check-alerts mode
    if args.check_alerts:
        try:
            with open(args.check_alerts, 'r') as f:
                current_metrics = json.load(f)

            baseline_metrics = {}
            if args.baseline and Path(args.baseline).exists():
                with open(args.baseline, 'r') as f:
                    baseline_metrics = json.load(f)

            alerts = comparator.check_alerts(current_metrics, baseline_metrics)

            if alerts:
                print("\n⚠️  Performance Alerts Detected:")
                for alert in alerts:
                    severity_icon = "🔴" if alert['severity'] == 'high' else "🟡"
                    print(f"  {severity_icon} [{alert['severity'].upper()}] {alert['message']}")
            else:
                print("\n✅ No performance alerts detected")

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump({
                        'alerts': alerts,
                        'timestamp': datetime.now().isoformat()
                    }, f, indent=2)

        except Exception as e:
            print(f"Error checking alerts: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle normal comparison mode
    if not args.current:
        print("Error: --current is required", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.current, 'r') as f:
            current_metrics = json.load(f)

        # Load baseline if provided, otherwise use target values
        baseline_metrics = {}
        if args.baseline and Path(args.baseline).exists():
            with open(args.baseline, 'r') as f:
                baseline_metrics = json.load(f)
        else:
            # Use target values as baseline
            scenario_config = baseline_defs.SCENARIOS[args.scenario]
            baseline_metrics = {k: v['target'] for k, v in scenario_config['metrics'].items()}

        # Compare metrics
        comparison = comparator.compare_to_baseline(current_metrics, baseline_metrics, args.scenario)

        # Check for alerts
        alerts = comparator.check_alerts(current_metrics, baseline_metrics)

        # Print summary
        print(f"\n📊 Baseline Comparison Report ({args.scenario.upper()} scenario)")
        print("=" * 60)

        for metric_name, result in comparison['metrics'].items():
            status = result['status']
            status_icon = "✅" if status == "pass" else "⚠️ " if status == "warn" else "❌"
            variance = result['variance_pct']
            print(f"{status_icon} {metric_name:20} | {result['current']:>8.2f} (baseline: {result['baseline']:>8.2f}, {variance:+6.1f}%)")

        print("-" * 60)
        print(f"Results: {comparison['summary']['passed']} passed, {comparison['summary']['warnings']} warnings, {comparison['summary']['failures']} failures")

        if alerts:
            print("\n⚠️  Alerts:")
            for alert in alerts:
                print(f"  - [{alert['severity'].upper()}] {alert['message']}")

        # Generate HTML report if requested
        if args.output:
            report_gen.generate_html_report(comparison, args.output, alerts)
            print(f"\n📄 HTML report saved to: {args.output}")

        # Exit with appropriate code
        if comparison['summary']['failures'] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

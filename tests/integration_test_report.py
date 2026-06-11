#!/usr/bin/env python3
"""
integration_test_report.py — Generate HTML Reports from Integration Test Results

Parses pytest JSON output and generates a comprehensive HTML report with:
- Summary statistics (passed/failed/skipped)
- Test execution times
- Detailed failure information
- Links to test code
- Timeline and performance graphs

Usage:
    python3 integration_test_report.py --json-input results.json --output report.html
    python3 integration_test_report.py --json-input data.json --output report.html --title "Custom Title"

Options:
    --json-input FILE       Path to pytest JSON report (required)
    --output FILE           Output HTML file path (default: integration_test_report.html)
    --title TITLE          Report title (default: Integration Test Report)
    --show-skipped         Include skipped tests in report
    --help                 Show this help message
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class TestReportGenerator:
    """Generate HTML report from pytest JSON test results."""

    def __init__(
        self,
        json_file: str,
        output_file: str = "integration_test_report.html",
        title: str = "Integration Test Report",
        show_skipped: bool = False,
    ):
        """Initialize report generator."""
        self.json_file = Path(json_file)
        self.output_file = Path(output_file)
        self.title = title
        self.show_skipped = show_skipped
        self.tests: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def load_json_report(self) -> bool:
        """Load and parse pytest JSON report."""
        if not self.json_file.exists():
            print(f"Error: JSON file not found: {self.json_file}", file=sys.stderr)
            return False

        try:
            with open(self.json_file, "r") as f:
                data = json.load(f)

            self.tests = data.get("tests", [])
            self.summary = data.get("summary", {})
            return True
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {self.json_file}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error reading {self.json_file}: {e}", file=sys.stderr)
            return False

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate test statistics."""
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t.get("outcome") == "passed")
        failed = sum(1 for t in self.tests if t.get("outcome") == "failed")
        skipped = sum(1 for t in self.tests if t.get("outcome") == "skipped")

        # Calculate execution times
        total_time = sum(t.get("duration", 0) for t in self.tests)
        slowest_tests = sorted(
            [t for t in self.tests if t.get("outcome") != "skipped"],
            key=lambda x: x.get("duration", 0),
            reverse=True,
        )[:5]

        pass_rate = (passed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_time": total_time,
            "pass_rate": pass_rate,
            "slowest_tests": slowest_tests,
        }

    def get_test_details(self, test: Dict[str, Any]) -> Dict[str, str]:
        """Extract and format test details."""
        name = test.get("nodeid", "Unknown")
        outcome = test.get("outcome", "unknown")
        duration = test.get("duration", 0)
        error_msg = ""

        if outcome == "failed":
            call_info = test.get("call", {})
            error_msg = call_info.get("longrepr", "No error details available")
            # Truncate very long error messages
            if len(error_msg) > 1000:
                error_msg = error_msg[:1000] + "..."

        return {
            "name": name,
            "outcome": outcome,
            "duration": f"{duration:.3f}s",
            "error_msg": error_msg,
        }

    def generate_html(self) -> str:
        """Generate HTML report content."""
        stats = self.calculate_statistics()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_parts = [
            self._html_header(timestamp),
            self._html_summary(stats),
            self._html_statistics_section(stats),
            self._html_tests_section(),
            self._html_footer(),
        ]

        return "\n".join(html_parts)

    def _html_header(self, timestamp: str) -> str:
        """Generate HTML header."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .content {{
            padding: 30px;
        }}

        .summary-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .summary-card.passed {{
            border-left-color: #28a745;
        }}

        .summary-card.failed {{
            border-left-color: #dc3545;
        }}

        .summary-card.skipped {{
            border-left-color: #ffc107;
        }}

        .summary-card h3 {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}

        .summary-card.passed .value {{ color: #28a745; }}
        .summary-card.failed .value {{ color: #dc3545; }}
        .summary-card.skipped .value {{ color: #ffc107; }}

        .section {{
            margin-bottom: 40px;
        }}

        .section h2 {{
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            color: #333;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .progress-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.85em;
        }}

        .progress-passed {{
            background: #28a745;
        }}

        .progress-failed {{
            background: #dc3545;
        }}

        .progress-skipped {{
            background: #ffc107;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}

        table thead {{
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }}

        table th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
        }}

        table td {{
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }}

        table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .test-name {{
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            color: #667eea;
        }}

        .test-passed {{
            color: #28a745;
            font-weight: bold;
        }}

        .test-failed {{
            color: #dc3545;
            font-weight: bold;
        }}

        .test-skipped {{
            color: #ffc107;
            font-weight: bold;
        }}

        .error-details {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 10px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 300px;
            overflow-y: auto;
        }}

        .error-details.severe {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-top: 1px solid #dee2e6;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}

        .metric {{
            display: inline-block;
            margin-right: 20px;
        }}

        .metric-label {{
            font-weight: 600;
            color: #333;
        }}

        .metric-value {{
            color: #667eea;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stats-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .stats-box h3 {{
            font-size: 0.95em;
            color: #666;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .slowest-test {{
            padding: 10px;
            background: white;
            border-left: 3px solid #667eea;
            margin-bottom: 10px;
            border-radius: 2px;
        }}

        .slowest-test-name {{
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85em;
            color: #333;
            margin-bottom: 5px;
        }}

        .slowest-test-time {{
            color: #dc3545;
            font-weight: bold;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .header {{ padding: 20px; }}
            .header h1 {{ font-size: 1.5em; }}
            .content {{ padding: 20px; }}
            .summary-row {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.title}</h1>
            <p>Generated: {timestamp}</p>
        </div>
        <div class="content">
"""

    def _html_summary(self, stats: Dict[str, Any]) -> str:
        """Generate summary cards."""
        total = stats["total"]
        passed = stats["passed"]
        failed = stats["failed"]
        skipped = stats["skipped"]
        pass_rate = stats["pass_rate"]

        return f"""
            <div class="summary-row">
                <div class="summary-card">
                    <h3>Total Tests</h3>
                    <div class="value">{total}</div>
                </div>
                <div class="summary-card passed">
                    <h3>Passed</h3>
                    <div class="value">{passed}</div>
                </div>
                <div class="summary-card failed">
                    <h3>Failed</h3>
                    <div class="value">{failed}</div>
                </div>
                <div class="summary-card skipped">
                    <h3>Skipped</h3>
                    <div class="value">{skipped}</div>
                </div>
                <div class="summary-card">
                    <h3>Pass Rate</h3>
                    <div class="value">{pass_rate:.1f}%</div>
                </div>
            </div>

            <div class="section">
                <h2>Overall Results</h2>
                <div class="progress-bar">
                    {'<div class="progress-segment progress-passed" style="width: ' + str(passed/total*100 if total > 0 else 0) + '%">' + (str(passed) if passed > 0 else '') + '</div>' if passed > 0 else ''}
                    {'<div class="progress-segment progress-failed" style="width: ' + str(failed/total*100 if total > 0 else 0) + '%">' + (str(failed) if failed > 0 else '') + '</div>' if failed > 0 else ''}
                    {'<div class="progress-segment progress-skipped" style="width: ' + str(skipped/total*100 if total > 0 else 0) + '%">' + (str(skipped) if skipped > 0 else '') + '</div>' if skipped > 0 else ''}
                </div>
            </div>
"""

    def _html_statistics_section(self, stats: Dict[str, Any]) -> str:
        """Generate statistics section."""
        total_time = stats["total_time"]
        slowest_tests = stats["slowest_tests"]

        slowest_html = ""
        if slowest_tests:
            for i, test in enumerate(slowest_tests, 1):
                test_details = self.get_test_details(test)
                slowest_html += f"""
                <div class="slowest-test">
                    <div class="slowest-test-name">{i}. {test_details['name']}</div>
                    <div class="slowest-test-time">Duration: {test_details['duration']}</div>
                </div>
"""

        return f"""
            <div class="section">
                <h2>Execution Statistics</h2>
                <div class="stats-grid">
                    <div class="stats-box">
                        <h3>Total Execution Time</h3>
                        <div style="font-size: 1.5em; color: #667eea; font-weight: bold;">
                            {total_time:.2f}s
                        </div>
                    </div>
                    <div class="stats-box">
                        <h3>Slowest Tests</h3>
                        {slowest_html}
                    </div>
                </div>
            </div>
"""

    def _html_tests_section(self) -> str:
        """Generate detailed tests section."""
        # Filter tests based on show_skipped flag
        tests_to_show = [
            t
            for t in self.tests
            if self.show_skipped or t.get("outcome") != "skipped"
        ]

        # Organize by outcome
        passed_tests = [t for t in tests_to_show if t.get("outcome") == "passed"]
        failed_tests = [t for t in tests_to_show if t.get("outcome") == "failed"]
        skipped_tests = [t for t in tests_to_show if t.get("outcome") == "skipped"]

        html = '<div class="section"><h2>Test Details</h2>'

        # Failed tests (with error details)
        if failed_tests:
            html += '<h3 style="color: #dc3545; margin-bottom: 15px;">Failed Tests</h3>'
            html += "<table><thead><tr><th>Test Name</th><th>Duration</th><th>Status</th></tr></thead><tbody>"
            for test in failed_tests:
                details = self.get_test_details(test)
                html += f"""
                <tr>
                    <td><span class="test-name">{details['name']}</span></td>
                    <td>{details['duration']}</td>
                    <td><span class="test-failed">FAILED</span></td>
                </tr>
"""
                if details["error_msg"]:
                    html += f"""
                <tr><td colspan="3">
                    <div class="error-details severe">{details['error_msg']}</div>
                </td></tr>
"""
            html += "</tbody></table>"

        # Passed tests
        if passed_tests:
            html += '<h3 style="color: #28a745; margin-bottom: 15px;">Passed Tests</h3>'
            html += "<table><thead><tr><th>Test Name</th><th>Duration</th><th>Status</th></tr></thead><tbody>"
            for test in passed_tests:
                details = self.get_test_details(test)
                html += f"""
                <tr>
                    <td><span class="test-name">{details['name']}</span></td>
                    <td>{details['duration']}</td>
                    <td><span class="test-passed">PASSED</span></td>
                </tr>
"""
            html += "</tbody></table>"

        # Skipped tests
        if skipped_tests and self.show_skipped:
            html += '<h3 style="color: #ffc107; margin-bottom: 15px;">Skipped Tests</h3>'
            html += "<table><thead><tr><th>Test Name</th><th>Status</th></tr></thead><tbody>"
            for test in skipped_tests:
                details = self.get_test_details(test)
                html += f"""
                <tr>
                    <td><span class="test-name">{details['name']}</span></td>
                    <td><span class="test-skipped">SKIPPED</span></td>
                </tr>
"""
            html += "</tbody></table>"

        html += "</div>"
        return html

    def _html_footer(self) -> str:
        """Generate HTML footer."""
        return f"""
        </div>
        <div class="footer">
            <p>Integration Test Report — Generated by integration_test_report.py</p>
            <p>Results file: {self.json_file}</p>
        </div>
    </div>
</body>
</html>
"""

    def generate(self) -> bool:
        """Load JSON, generate HTML, and write to output file."""
        if not self.load_json_report():
            return False

        html_content = self.generate_html()

        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_file, "w") as f:
                f.write(html_content)

            print(f"HTML report generated: {self.output_file}")
            return True
        except Exception as e:
            print(f"Error writing HTML report: {e}", file=sys.stderr)
            return False


def main():
    """Parse arguments and generate report."""
    parser = argparse.ArgumentParser(
        description="Generate HTML reports from pytest JSON test results"
    )
    parser.add_argument(
        "--json-input",
        required=True,
        help="Path to pytest JSON report file",
    )
    parser.add_argument(
        "--output",
        default="integration_test_report.html",
        help="Output HTML file path (default: integration_test_report.html)",
    )
    parser.add_argument(
        "--title",
        default="Integration Test Report",
        help="Report title (default: Integration Test Report)",
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Include skipped tests in report",
    )
    parser.add_argument(
        "--help",
        "-h",
        action="store_true",
        help="Show help message",
    )

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        return 0

    generator = TestReportGenerator(
        json_file=args.json_input,
        output_file=args.output,
        title=args.title,
        show_skipped=args.show_skipped,
    )

    if generator.generate():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

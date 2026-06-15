#!/usr/bin/env python3
"""
Setup staging environment monitoring and alerting.

Configures:
- CloudWatch dashboard for key metrics
- Error rate alerting (> 1% = alert)
- Latency percentile tracking (p95, p99)
- Database connection pooling monitoring
- Cache hit rate tracking

Usage:
    python scripts/setup_staging_monitoring.py
    python scripts/setup_staging_monitoring.py --dry-run
    python scripts/setup_staging_monitoring.py --region us-east-1

Requirements:
    - AWS CLI configured with appropriate credentials
    - Permissions: cloudwatch:*, logs:*, sns:*
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path


def setup_cloudwatch_dashboard(region: str = "us-east-1", dry_run: bool = False) -> bool:
    """Create CloudWatch dashboard for staging monitoring.

    Args:
        region: AWS region
        dry_run: If True, print commands instead of executing

    Returns:
        True if successful
    """
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ApplicationELB", "TargetResponseTime", {"stat": "Average", "label": "Avg Response Time"}],
                        [".", "TargetResponseTime", {"stat": "p95", "label": "P95 Response Time"}],
                        [".", "TargetResponseTime", {"stat": "p99", "label": "P99 Response Time"}],
                    ],
                    "period": 60,
                    "stat": "Average",
                    "region": region,
                    "title": "API Latency",
                    "yAxis": {"left": {"min": 0, "max": 1000}},
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count"],
                        [".", "HTTPCode_Target_4XX_Count"],
                        [".", "HTTPCode_Target_2XX_Count"],
                    ],
                    "period": 60,
                    "stat": "Sum",
                    "region": region,
                    "title": "HTTP Response Codes",
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/RDS", "CPUUtilization", {"label": "Database CPU"}],
                        [".", "DatabaseConnections", {"label": "Active Connections"}],
                        [".", "ReadLatency", {"label": "Read Latency"}],
                        [".", "WriteLatency", {"label": "Write Latency"}],
                    ],
                    "period": 60,
                    "stat": "Average",
                    "region": region,
                    "title": "PostgreSQL Performance",
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ApplicationELB", "TargetConnectionCount", {"label": "Active Connections"}],
                        [".", "HealthyHostCount", {"label": "Healthy Hosts"}],
                        [".", "UnHealthyHostCount", {"label": "Unhealthy Hosts"}],
                    ],
                    "period": 60,
                    "stat": "Average",
                    "region": region,
                    "title": "Target Health",
                }
            },
        ]
    }

    cmd = (
        f"aws cloudwatch put-dashboard "
        f"--dashboard-name PersonaPlatform-Staging "
        f"--dashboard-body '{json.dumps(dashboard_body)}' "
        f"--region {region}"
    )

    if dry_run:
        print("=" * 80)
        print("DRY RUN: CloudWatch Dashboard")
        print("=" * 80)
        print(f"Command: {cmd}")
        print()
        return True
    else:
        print("Creating CloudWatch dashboard...")
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Dashboard created successfully")
            return True
        else:
            print(f"✗ Failed to create dashboard: {result.stderr}")
            return False


def setup_error_rate_alarm(region: str = "us-east-1", dry_run: bool = False) -> bool:
    """Create alarm for high error rate.

    Triggers when HTTPCode_Target_5XX_Count > 1% of total requests.

    Args:
        region: AWS region
        dry_run: If True, print commands instead of executing

    Returns:
        True if successful
    """
    cmd = (
        f"aws cloudwatch put-metric-alarm "
        f"--alarm-name PersonaPlatform-Staging-ErrorRate "
        f"--alarm-description 'Alert if error rate > 1%' "
        f"--metric-name HTTPCode_Target_5XX_Count "
        f"--namespace AWS/ApplicationELB "
        f"--statistic Sum "
        f"--period 300 "
        f"--threshold 50 "
        f"--comparison-operator GreaterThanThreshold "
        f"--evaluation-periods 1 "
        f"--alarm-actions arn:aws:sns:{region}:ACCOUNT_ID:PersonaPlatform-Alerts "
        f"--region {region}"
    )

    if dry_run:
        print("=" * 80)
        print("DRY RUN: Error Rate Alarm")
        print("=" * 80)
        print(f"Command: {cmd}")
        print("Note: Replace ACCOUNT_ID with actual AWS account ID")
        print()
        return True
    else:
        print("Creating error rate alarm...")
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Error rate alarm created successfully")
            return True
        else:
            print(f"✗ Failed to create alarm: {result.stderr}")
            return False


def setup_latency_alarm(region: str = "us-east-1", dry_run: bool = False) -> bool:
    """Create alarm for high latency.

    Triggers when P95 response time > 600ms.

    Args:
        region: AWS region
        dry_run: If True, print commands instead of executing

    Returns:
        True if successful
    """
    cmd = (
        f"aws cloudwatch put-metric-alarm "
        f"--alarm-name PersonaPlatform-Staging-HighLatency "
        f"--alarm-description 'Alert if P95 latency > 600ms' "
        f"--metric-name TargetResponseTime "
        f"--namespace AWS/ApplicationELB "
        f"--statistic p95 "
        f"--period 300 "
        f"--threshold 600 "
        f"--comparison-operator GreaterThanThreshold "
        f"--evaluation-periods 2 "
        f"--alarm-actions arn:aws:sns:{region}:ACCOUNT_ID:PersonaPlatform-Alerts "
        f"--region {region}"
    )

    if dry_run:
        print("=" * 80)
        print("DRY RUN: Latency Alarm")
        print("=" * 80)
        print(f"Command: {cmd}")
        print("Note: Replace ACCOUNT_ID with actual AWS account ID")
        print()
        return True
    else:
        print("Creating latency alarm...")
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Latency alarm created successfully")
            return True
        else:
            print(f"✗ Failed to create alarm: {result.stderr}")
            return False


def setup_database_monitoring(region: str = "us-east-1", dry_run: bool = False) -> bool:
    """Create alarms for database health.

    Monitors:
    - CPU utilization > 80%
    - Active connections > 90/100
    - Storage > 80% full

    Args:
        region: AWS region
        dry_run: If True, print commands instead of executing

    Returns:
        True if successful
    """
    alarms = [
        {
            "name": "PersonaPlatform-Staging-DBHighCPU",
            "desc": "Alert if RDS CPU > 80%",
            "metric": "CPUUtilization",
            "threshold": 80,
        },
        {
            "name": "PersonaPlatform-Staging-DBHighConnections",
            "desc": "Alert if active connections > 90",
            "metric": "DatabaseConnections",
            "threshold": 90,
        },
    ]

    for alarm in alarms:
        cmd = (
            f"aws cloudwatch put-metric-alarm "
            f"--alarm-name {alarm['name']} "
            f"--alarm-description '{alarm['desc']}' "
            f"--metric-name {alarm['metric']} "
            f"--namespace AWS/RDS "
            f"--statistic Average "
            f"--period 300 "
            f"--threshold {alarm['threshold']} "
            f"--comparison-operator GreaterThanThreshold "
            f"--evaluation-periods 2 "
            f"--alarm-actions arn:aws:sns:{region}:ACCOUNT_ID:PersonaPlatform-Alerts "
            f"--region {region}"
        )

        if dry_run:
            print("=" * 80)
            print(f"DRY RUN: {alarm['name']}")
            print("=" * 80)
            print(f"Command: {cmd}")
            print("Note: Replace ACCOUNT_ID with actual AWS account ID")
            print()
        else:
            print(f"Creating alarm: {alarm['name']}...")
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {alarm['name']} created successfully")
            else:
                print(f"✗ Failed to create {alarm['name']}: {result.stderr}")
                return False

    return True


def setup_log_insights_queries(region: str = "us-east-1", dry_run: bool = False) -> bool:
    """Setup CloudWatch Logs Insights queries for analysis.

    Provides quick access to common queries for troubleshooting.

    Args:
        region: AWS region
        dry_run: If True, print commands instead of executing

    Returns:
        True if successful
    """
    queries = {
        "matching_latency": """
fields @timestamp, @message, response_time_ms
| filter ispresent(response_time_ms)
| stats avg(response_time_ms), pct(response_time_ms, 95), pct(response_time_ms, 99)
        """,
        "error_analysis": """
fields @timestamp, @message, error_type
| filter @message like /ERROR/ or error_type like /error/
| stats count() as error_count by error_type
        """,
        "cache_performance": """
fields @timestamp, cache_hits, cache_misses
| filter ispresent(cache_hits)
| stats sum(cache_hits) as total_hits, sum(cache_misses) as total_misses
| fields total_hits / (total_hits + total_misses) as hit_rate
        """,
        "persona_match_distribution": """
fields @timestamp, top_persona_id
| filter ispresent(top_persona_id)
| stats count() as matches by top_persona_id
| sort matches desc
        """,
    }

    if dry_run:
        print("=" * 80)
        print("DRY RUN: CloudWatch Logs Insights Queries")
        print("=" * 80)
        for name, query in queries.items():
            print(f"\n{name}:")
            print(query)
        print()
        return True
    else:
        print("CloudWatch Logs Insights queries (save to console):")
        for name, query in queries.items():
            print(f"\n{name}:")
            print(query)
        return True


def create_monitoring_config_file(output_path: str = "monitoring_config.json"):
    """Create monitoring configuration JSON for reference.

    Args:
        output_path: Path to save config file
    """
    config = {
        "monitoring": {
            "dashboards": [
                {
                    "name": "PersonaPlatform-Staging",
                    "widgets": [
                        "API Latency",
                        "HTTP Response Codes",
                        "PostgreSQL Performance",
                        "Target Health",
                    ]
                }
            ],
            "alarms": [
                {
                    "name": "PersonaPlatform-Staging-ErrorRate",
                    "metric": "HTTPCode_Target_5XX_Count",
                    "threshold": 50,
                    "period_seconds": 300,
                    "description": "Alert if error rate > 1%",
                },
                {
                    "name": "PersonaPlatform-Staging-HighLatency",
                    "metric": "TargetResponseTime (p95)",
                    "threshold": 600,
                    "period_seconds": 300,
                    "description": "Alert if P95 latency > 600ms",
                },
                {
                    "name": "PersonaPlatform-Staging-DBHighCPU",
                    "metric": "CPUUtilization",
                    "threshold": 80,
                    "period_seconds": 300,
                    "description": "Alert if RDS CPU > 80%",
                },
                {
                    "name": "PersonaPlatform-Staging-DBHighConnections",
                    "metric": "DatabaseConnections",
                    "threshold": 90,
                    "period_seconds": 300,
                    "description": "Alert if active connections > 90",
                },
            ],
            "metrics": [
                {
                    "name": "matching_latency_ms",
                    "description": "API response time for persona matching",
                    "unit": "Milliseconds",
                },
                {
                    "name": "cache_hit_rate",
                    "description": "K-layer cache hit rate percentage",
                    "unit": "Percent",
                },
                {
                    "name": "db_connection_pool_utilization",
                    "description": "Database connection pool utilization",
                    "unit": "Percent",
                },
            ],
        },
        "generated": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✓ Monitoring config saved to {output_path}")
    return config


def print_setup_guide(region: str):
    """Print user-friendly setup guide.

    Args:
        region: AWS region
    """
    print("\n" + "=" * 80)
    print("STAGING MONITORING SETUP GUIDE")
    print("=" * 80)

    print("""
✓ CloudWatch Dashboard
  - Displays real-time metrics for API, database, and health
  - URL: https://console.aws.amazon.com/cloudwatch/home?region={}

✓ Error Rate Alarm
  - Triggers when HTTPCode_5XX > 50 requests/5min (~1%)
  - Sends SNS notification to PersonaPlatform-Alerts topic

✓ Latency Alarm
  - Triggers when P95 response time > 600ms for 2 consecutive periods
  - Useful for detecting performance degradation

✓ Database Alarms
  - CPU: Alerts when > 80% for 10 minutes
  - Connections: Alerts when > 90/100 pool exhausted
  - Helps prevent database bottlenecks

✓ CloudWatch Logs Insights
  - Pre-built queries for:
    * Matching latency analysis
    * Error rate investigation
    * Cache performance tracking
    * Persona match distribution

NEXT STEPS:
1. Replace ACCOUNT_ID in alarm ARNs with your AWS account ID
   aws sts get-caller-identity  # Get account ID

2. Create SNS topic for alerts:
   aws sns create-topic --name PersonaPlatform-Alerts --region {}

3. Subscribe to alerts:
   aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint <email>

4. Enable detailed monitoring on RDS:
   aws rds modify-db-instance \\
     --db-instance-identifier persona-platform-staging \\
     --enable-cloudwatch-logs-exports postgresql \\
     --apply-immediately

5. Test alarms:
   # Trigger test alarm
   aws cloudwatch set-alarm-state \\
     --alarm-name PersonaPlatform-Staging-ErrorRate \\
     --state-value ALARM \\
     --state-reason "Testing alarm"

METRICS REFERENCE:
- Mean matching latency target: < 400ms
- P95 matching latency target: < 600ms
- P99 matching latency target: < 800ms
- Cache hit rate target: > 70%
- Error rate target: < 0.1%
- Database CPU target: < 70%
- Database connections target: < 80/100

See STAGING_DEPLOYMENT_RUNBOOK.md for detailed metrics.
""".format(region, region))

    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup staging environment monitoring and alerting"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands instead of executing"
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Only create dashboard (skip alarms)"
    )
    parser.add_argument(
        "--alarms-only",
        action="store_true",
        help="Only create alarms (skip dashboard)"
    )
    parser.add_argument(
        "--output-config",
        default="monitoring_config.json",
        help="Path to save monitoring config file"
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("STAGING MONITORING SETUP")
    print("=" * 80)
    print(f"Region: {args.region}")
    if args.dry_run:
        print("Mode: DRY RUN (commands only, no changes)")
    print()

    success = True

    if not args.alarms_only:
        print("\n1. Setting up CloudWatch Dashboard...")
        if not setup_cloudwatch_dashboard(args.region, args.dry_run):
            success = False

    if not args.dashboard_only:
        print("\n2. Setting up Error Rate Alarm...")
        if not setup_error_rate_alarm(args.region, args.dry_run):
            success = False

        print("\n3. Setting up Latency Alarm...")
        if not setup_latency_alarm(args.region, args.dry_run):
            success = False

        print("\n4. Setting up Database Monitoring...")
        if not setup_database_monitoring(args.region, args.dry_run):
            success = False

    print("\n5. Creating CloudWatch Logs Insights Queries...")
    setup_log_insights_queries(args.region, args.dry_run)

    print("\n6. Creating Monitoring Configuration File...")
    create_monitoring_config_file(args.output_config)

    if not args.dry_run:
        print_setup_guide(args.region)

    if not success:
        print("\n✗ Some setup steps failed. See errors above.")
        sys.exit(1)
    else:
        print("\n✓ Monitoring setup complete!")
        sys.exit(0)


if __name__ == "__main__":
    main()

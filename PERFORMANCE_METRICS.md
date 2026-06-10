# Performance Regression Detection (H93)

**Status:** Baseline tracking with automated regression detection and alerting  
**API Endpoint:** `/performance`  
**Database Tables:** performance_metrics, performance_baselines  
**CI/CD Integration:** GitHub Actions workflow for automated detection

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Metric Types](#metric-types)
4. [Regression Detection](#regression-detection)
5. [API Reference](#api-reference)
6. [CI/CD Integration](#cicd-integration)
7. [Examples](#examples)
8. [Alerting & Actions](#alerting--actions)
9. [Best Practices](#best-practices)

---

## Overview

**Performance regression detection** automatically identifies when deployments degrade performance:

- ✅ **Baseline Tracking** — Capture performance metrics (latency, error rate, throughput)
- ✅ **Automated Detection** — Compare new metrics against historical baseline
- ✅ **Severity Classification** — Critical (>50%), High (25-50%), Medium (10-25%), Low (5-10%)
- ✅ **Statistical Analysis** — P95 latency, standard deviation, confidence intervals
- ✅ **Smart Alerting** — Only alert on significant regressions (>threshold + confidence)
- ✅ **CI/CD Integration** — Automated checks on every deployment
- ✅ **Actionable Insights** — Recommended actions for each regression

**Key metrics tracked:**
| Metric | Type | Typical Baseline |
|--------|------|-----------------|
| Response Time (p95) | Milliseconds | 100-200ms |
| Error Rate | Percent | 0.5-1.0% |
| Throughput | Requests/sec | 100-500 req/s |
| Database Query Time | Milliseconds | 10-50ms |
| Memory Usage | Megabytes | 500-2000MB |
| CPU Usage | Percent | 20-50% |

---

## How It Works

### 1. Baseline Creation

```
Collect metrics during stable period (1+ hour)
         ↓
Calculate statistics:
  - p50, p95, p99 percentiles
  - mean, standard deviation
  - min/max values
         ↓
Store as PerformanceBaseline
  {
    p95: 150ms,
    stddev: 25ms,
    sample_count: 1200,
    created_at: 2024-06-10
  }
```

### 2. Deployment & Monitoring

```
Code deployed
    ↓
Collect new metrics
    ↓
Calculate current p95
    ↓
Compare to baseline:
  ((150ms - baseline) / baseline * 100)
    ↓
Determine severity:
  < 5%:   No alert
  5-10%:  Low (monitor)
  10-25%: Medium (investigate)
  25-50%: High (alert)
  > 50%:  Critical (urgent)
```

### 3. Alerting & Action

```
Regression detected
    ↓
Format alert with severity
    ↓
Send to Slack/email
    ↓
Recommend action:
  CRITICAL: Consider rollback
  HIGH:     Investigate changes
  MEDIUM:   Monitor closely
```

---

## Metric Types

### Response Time (ms)

```
Measures: HTTP request processing time (p50, p95, p99)
Threshold: > 20% increase is concerning
Causes: Code changes, database issues, external API latency

Example:
  Baseline p95: 150ms
  Current p95:  210ms (40% increase)
  → HIGH severity
```

### Error Rate (percent)

```
Measures: HTTP 5xx and 4xx errors as percent of total
Threshold: > 0.5% increase is concerning
Causes: Bugs, dependency issues, configuration errors

Example:
  Baseline: 0.8% errors
  Current:  2.1% errors (162% increase)
  → CRITICAL severity
```

### Throughput (requests/sec)

```
Measures: API requests per second
Threshold: > 15% decrease is concerning
Causes: Resource exhaustion, bottlenecks, concurrency issues

Example:
  Baseline: 500 req/sec
  Current:  380 req/sec (24% decrease)
  → HIGH severity
```

### Database Query Time (ms)

```
Measures: P95 latency of database queries
Threshold: > 10% increase is concerning
Causes: Missing indexes, slow queries, lock contention

Example:
  Baseline p95: 25ms
  Current p95:  40ms (60% increase)
  → CRITICAL severity
```

### Memory Usage (MB)

```
Measures: Application memory consumption
Threshold: > 25% increase is concerning
Causes: Memory leaks, inefficient caching, large datasets

Example:
  Baseline: 800MB
  Current:  1200MB (50% increase)
  → HIGH severity
```

### CPU Usage (percent)

```
Measures: CPU utilization (0-100%)
Threshold: > 20 percentage points increase is concerning
Causes: Infinite loops, inefficient algorithms, missing optimization

Example:
  Baseline: 35%
  Current:  65% (30pp increase)
  → HIGH severity
```

---

## Regression Detection

### Severity Calculation

```python
def calculate_severity(percent_change):
    if percent_change < 5:
        return LOW        # Natural variation
    elif percent_change < 10:
        return LOW        # Minor degradation
    elif percent_change < 25:
        return MEDIUM     # Noticeable change
    elif percent_change < 50:
        return HIGH       # Significant change
    else:
        return CRITICAL   # Major degradation
```

### Confidence Score

Regression confidence based on:
- **Sample size** — More samples = higher confidence
- **Variability** — Lower stddev = higher confidence
- **Consistency** — All metrics trending same direction

```
Confidence = min(samples / 100, 1.0)

Examples:
  10 samples:   10% confidence
  50 samples:   50% confidence
  100+ samples: 100% confidence
```

### Alert Conditions

```
Alert triggered if:
  - severity = CRITICAL (>50% change), OR
  - severity = HIGH (25-50% change), OR
  - severity = MEDIUM (10-25% change) AND confidence > 70%

Examples:
  ✅ Alert: 60% increase + 100% confidence = CRITICAL
  ✅ Alert: 30% increase + 80% confidence = HIGH
  ✅ Alert: 15% increase + 75% confidence = MEDIUM (high confidence)
  ❌ No alert: 15% increase + 40% confidence = MEDIUM (low confidence)
```

---

## API Reference

### Record Metric

```
POST /performance/metrics/record
```

**Request:**
```json
{
  "metric_type": "response_time_ms",
  "value": 145,
  "endpoint": "/v1/compile"
}
```

**Response:**
```json
{
  "message": "Metric recorded successfully",
  "metric_type": "response_time_ms",
  "value": 145,
  "endpoint": "/v1/compile"
}
```

### List Metrics

```
GET /performance/metrics?metric_type=response_time_ms&hours=1
```

**Response:**
```json
{
  "metric_type": "response_time_ms",
  "endpoint": null,
  "hours": 1,
  "count": 150,
  "metrics": [
    {
      "value": 145,
      "recorded_at": "2024-06-10T15:30:00Z",
      "tags": {}
    }
  ]
}
```

### Create Baseline

```
POST /performance/baselines/create?metric_type=response_time_ms&hours=1
```

**Response:**
```json
{
  "message": "Baseline created successfully",
  "metric_type": "response_time_ms",
  "sample_count": 200,
  "p50": 120,
  "p95": 150,
  "p99": 180,
  "mean": 130,
  "stddev": 20,
  "created_at": "2024-06-10T16:00:00Z"
}
```

### Check for Regressions

```
GET /performance/regressions/check?hours=1&threshold_percent=10
```

**Response:**
```json
{
  "window_hours": 1,
  "threshold_percent": 10,
  "total_metrics_checked": 4,
  "regressions_detected": 1,
  "alerts": [
    {
      "title": "⚠️ Performance Regression Detected",
      "metric": "response_time_ms",
      "endpoint": "global",
      "severity": "HIGH",
      "change_percent": "+32.5%",
      "baseline_p95": "150.00ms",
      "current_p95": "198.75ms",
      "explanation": "response_time_ms increased by 32.5% (baseline: 150.00, current: 198.75) — HIGH: 25-50% degradation",
      "confidence": "92%",
      "action": "Investigate recent code changes and deployments"
    }
  ],
  "all_results": [...]
}
```

### Detect Endpoint Regression

```
POST /performance/regressions/detect?metric_type=response_time_ms&endpoint=/v1/compile
```

**Response:**
```json
{
  "metric_type": "response_time_ms",
  "endpoint": "/v1/compile",
  "is_regression": true,
  "severity": "HIGH",
  "percent_change": 32.5,
  "baseline": {
    "p50": 120,
    "p95": 150,
    "p99": 180,
    "mean": 130,
    "stddev": 20,
    "sample_count": 300,
    "created_at": "2024-06-10T15:00:00Z"
  },
  "current": {
    "p95": 198,
    "samples": 45
  },
  "explanation": "response_time_ms increased by 32.5% (baseline: 150.00, current: 198.75) — HIGH: 25-50% degradation",
  "confidence": 0.92,
  "alert": {...}
}
```

### Performance Dashboard

```
GET /performance/dashboard/summary?hours=24
```

**Response:**
```json
{
  "window_hours": 24,
  "summary_time": "2024-06-10T16:30:00Z",
  "metrics": {
    "response_time_ms": {
      "count": 2500,
      "current_p95": 155,
      "mean": 128,
      "baseline_p95": 150,
      "baseline_exists": true
    },
    "error_rate_percent": {
      "count": 2500,
      "current_p95": 0.9,
      "mean": 0.75,
      "baseline_p95": 0.8,
      "baseline_exists": true
    }
  }
}
```

---

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/performance-check.yml`:

```yaml
name: Performance Regression Check (H93)

on:
  pull_request:
    branches: [main, develop]
  workflow_run:
    workflows: ["CI - Multi-Python Matrix Tests"]
    types: [completed]

jobs:
  performance-check:
    name: Check for Performance Regressions
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Run load test on PR branch
        run: |
          # Run light load test (10 concurrent users, 2 minutes)
          python tests/load_test_payments.py \
            --host https://pr-${{ github.event.pull_request.number }}.persona-hub.com \
            --users 10 \
            --run-time 120 \
            --output metrics_pr.json

      - name: Get baseline metrics (main branch)
        run: |
          curl -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            https://api.persona-hub.com/performance/baselines?metric_type=response_time_ms \
            > baseline.json

      - name: Compare metrics
        id: compare
        run: |
          python scripts/compare_metrics.py \
            --baseline baseline.json \
            --current metrics_pr.json \
            --threshold 15 \
            --output comparison.json

      - name: Check for regressions
        run: |
          curl -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            https://api.persona-hub.com/performance/regressions/check?hours=1 \
            > regressions.json
          
          # If regressions found, exit with error
          if [ $(cat regressions.json | jq '.regressions_detected') -gt 0 ]; then
            echo "Performance regressions detected!"
            cat regressions.json | jq '.alerts'
            exit 1
          fi

      - name: Comment PR with results
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const comparison = JSON.parse(fs.readFileSync('comparison.json'));
            
            const comment = `## Performance Check Results
            
| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| Response Time (p95) | ${comparison.baseline_p95}ms | ${comparison.current_p95}ms | ${comparison.percent_change}% |
| Error Rate | ${comparison.baseline_error}% | ${comparison.current_error}% | ${comparison.error_change}% |

${comparison.has_regression ? '⚠️ Performance regression detected!' : '✅ Performance within acceptable range'}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Comparison Script

Create `scripts/compare_metrics.py`:

```python
#!/usr/bin/env python3
"""Compare load test metrics against baseline."""

import json
import sys
from argparse import ArgumentParser

def main():
    parser = ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--threshold", type=float, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.baseline) as f:
        baseline = json.load(f)
    
    with open(args.current) as f:
        current = json.load(f)

    # Calculate percent change
    baseline_p95 = baseline.get("response_time_p95", 0)
    current_p95 = current.get("response_time_p95", 0)
    percent_change = ((current_p95 - baseline_p95) / baseline_p95 * 100) if baseline_p95 > 0 else 0

    has_regression = percent_change > args.threshold

    result = {
        "baseline_p95": baseline_p95,
        "current_p95": current_p95,
        "percent_change": round(percent_change, 1),
        "has_regression": has_regression,
        "threshold": args.threshold,
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Baseline p95: {baseline_p95}ms")
    print(f"Current p95:  {current_p95}ms")
    print(f"Change:       {percent_change:+.1f}%")
    print(f"Regression:   {'YES' if has_regression else 'NO'}")

    return 1 if has_regression else 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Examples

### Example 1: Manual Baseline Creation

```bash
# 1. Run application in stable state for 1 hour
# Collect response time metrics

# 2. Create baseline
curl -X POST http://localhost:8000/performance/baselines/create \
  -H "X-API-Key: prs_..." \
  -d "metric_type=response_time_ms&hours=1"

# Response:
# {
#   "p95": 150,
#   "stddev": 20,
#   "sample_count": 600,
#   "created_at": "2024-06-10T16:00:00Z"
# }

# 3. Deploy new code
git push origin main

# 4. After deployment, check for regressions
curl http://localhost:8000/performance/regressions/check?hours=1 \
  -H "X-API-Key: prs_..."

# Response shows if regression detected
```

### Example 2: Automated CI/CD Check

```bash
# GitHub Actions workflow runs on every PR:

# 1. Run load test on PR branch
pytest tests/load_test_payments.py --record-metrics

# 2. Compare against main branch baseline
python scripts/compare_metrics.py --threshold 15

# 3. If > 15% degradation: fail PR check
# Output: "Performance regression detected: p95 latency increased by 32%"
```

### Example 3: Incident Response

```bash
# Production issue: Response times spiking

# 1. Check regressions
curl https://api.persona-hub.com/performance/regressions/check?hours=1

# Response:
# "CRITICAL: response_time_ms increased by 65%"
# "Action: Consider rollback"

# 2. Rollback to previous version
git revert HEAD
git push origin main

# 3. Verify metrics return to baseline
# p95 latency drops from 250ms back to 150ms

# 4. Investigate root cause (database query? external API?)
```

---

## Alerting & Actions

### Severity-Based Response

| Severity | Threshold | Action |
|----------|-----------|--------|
| CRITICAL | > 50% | Immediate: Page on-call, consider rollback |
| HIGH | 25-50% | Urgent: Investigate, prepare rollback |
| MEDIUM | 10-25% | Important: Review changes, monitor |
| LOW | 5-10% | Info: Log, observe trend |

### Slack Alert Template

```
🚨 CRITICAL Performance Regression

Metric: Response Time (p95)
Endpoint: /v1/compile
Change: +65% (150ms → 247ms)
Confidence: 98%

Baseline: 150ms ± 20ms (300 samples)
Current: 247ms (45 samples)

⚡ Recommended Action:
  1. Check recent deployments
  2. Review database queries (/v1/compile endpoint)
  3. Check external API latency
  4. If critical: git revert + deploy

📊 View: https://dashboard.persona-hub.com/perf?hours=1
```

---

## Best Practices

### 1. Baseline Stability

```
✅ Create baselines during stable periods
   - Full day of production traffic (not peak)
   - After known good deployment
   - With diverse user behavior

❌ Avoid creating baselines during:
   - Maintenance windows
   - High traffic spikes
   - Known issues
```

### 2. Threshold Tuning

```
✅ Conservative thresholds (catch real regressions):
   - Response time: 10-15% increase
   - Error rate: 25% increase
   - Throughput: 15% decrease

❌ Too aggressive (false positives):
   - Response time: > 3% increase
   - Error rate: > 5% increase
   - Throughput: > 5% decrease

❌ Too lenient (miss real issues):
   - Response time: > 50% increase
   - Error rate: > 100% increase
```

### 3. Metric Collection

```python
# ✅ Do: Record at appropriate granularity
record_metric(
    db,
    MetricType.RESPONSE_TIME,
    value=145,
    endpoint="/v1/compile"  # Per-endpoint tracking
)

# ❌ Don't: Record every single request (data explosion)
# Instead: Sample 1/100 or aggregate in batches
```

### 4. Baseline Refresh

```
Refresh baselines periodically:
- Weekly: Minor tuning
- Monthly: Full regeneration
- After major changes: Immediate refresh

Example:
  POST /performance/baselines/create \
    ?metric_type=response_time_ms&hours=4
```

### 5. Alerting Fatigue

```
✅ Multi-criteria alerts (reduce noise):
  - severity = CRITICAL, OR
  - severity = HIGH, OR
  - (severity = MEDIUM AND confidence > 70%)

✅ Gradual escalation:
  - First 5 min: Log only
  - 5-15 min: Slack notification
  - 15+ min: Page on-call
```

---

## Troubleshooting

### Issue: False Positive Regressions

```
Cause: High natural variation in metrics
Solution:
  1. Increase sample size for baseline (use 4+ hours)
  2. Increase confidence threshold (require > 80%)
  3. Review stddev: high stddev = high variation
```

### Issue: Baseline Drift

```
Cause: Gradual performance degradation over time
Solution:
  1. Refresh baseline monthly
  2. Monitor trend: is p95 slowly creeping up?
  3. Investigate root cause (missing indexes, leaks)
```

### Issue: Missing Metrics

```
Cause: Metrics not being recorded
Solution:
  1. Verify load test running: pytest tests/load_test_*.py
  2. Check metric recording: POST /performance/metrics/record
  3. Verify database: SELECT COUNT(*) FROM performance_metrics
```

---

## References

- [Performance Testing Best Practices](https://www.softwaretestinghelp.com/performance-testing/)
- [Statistical Regression Analysis](https://en.wikipedia.org/wiki/Regression_analysis)
- [Canary Deployments](CANARY_DEPLOYMENTS.md)
- [Load Testing Guide](LOAD_TESTING.md)

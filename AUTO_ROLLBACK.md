# Automatic Rollback (H94) — Self-Healing Deployments

**Status:** Automatic error detection and rollback with manual approval option  
**API Endpoint:** `/rollback`  
**Database Tables:** rollback_policies, rollback_history  
**CI/CD Integration:** GitHub Actions automated trigger

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Rollback Triggers](#rollback-triggers)
4. [Configuration](#configuration)
5. [API Reference](#api-reference)
6. [GitHub Actions Integration](#github-actions-integration)
7. [Examples](#examples)
8. [Safety Mechanisms](#safety-mechanisms)
9. [Incident Response](#incident-response)

---

## Overview

**Automatic rollback** enables self-healing deployments by:

- ✅ **Continuous Monitoring** — Track error rates and latency in real-time
- ✅ **Automatic Detection** — Identify spikes that indicate problems
- ✅ **Decision Making** — Evaluate if rollback is appropriate
- ✅ **Safe Execution** — Respect cooldown periods and rate limits
- ✅ **Optional Approval** — Manual approval flow for critical systems
- ✅ **Incident Tracking** — Full audit trail of rollbacks
- ✅ **Recovery Verification** — Confirm metrics return to baseline

**Benefits:**
- 🚀 **Fast Recovery** — Automated rollback < 2 minutes
- 📊 **Reduced MTTR** — Mean Time To Recovery drops significantly
- 🎯 **Confidence** — Deploy multiple times daily with confidence
- 🛡️ **Safety** — Prevents prolonged outages from bad deployments
- 📈 **Data-Driven** — Rollback decisions based on metrics, not intuition

**Typical Timeline:**
```
00:00 - Bad deployment goes live
00:15 - Error rate spikes to 5% (vs 0.8% baseline)
00:18 - System detects spike, decides to rollback
00:20 - Rollback initiated (previous version deployed)
00:22 - Health checks pass, error rate back to 0.8%
00:23 - Incident resolved, team notified
```

---

## How It Works

### 1. Monitoring Phase

```
Every minute (continuous):
  - Collect error rate: SUM(5xx errors) / SUM(total requests)
  - Collect latency: p95 response time
  - Compare to baseline (calculated from previous stable period)
```

### 2. Detection Phase

```
If error_rate_current > baseline * 150%:  // 150% increase = 1.5x
  → ERROR_RATE_SPIKE detected
  → severity = HIGH

If latency_current > baseline * 150%:
  → LATENCY_DEGRADATION detected
  → severity = MEDIUM-HIGH
```

### 3. Evaluation Phase

```
Evaluate decision:
  - Is policy enabled? YES → continue
  - Are metrics above threshold? YES → continue
  - Sufficient samples? YES → continue
  - In cooldown period? NO → continue
  - Exceeded max rollbacks/hour? NO → continue
  
→ DECISION: ROLLBACK (confidence: 95%)
```

### 4. Execution Phase

```
If policy.require_approval:
  1. Send alert with approval link
  2. Wait for manual approval (configurable timeout)
  3. Execute rollback

If policy.require_approval = false:
  1. Execute rollback immediately
  2. Send incident notification
```

### 5. Recovery Phase

```
After rollback:
  1. Deploy previous version (< 30 sec)
  2. Wait for pods to become healthy (< 60 sec)
  3. Collect metrics for 2 minutes
  4. Verify error rate back to baseline
  5. Mark rollback as COMPLETED
  6. Send recovery notification to team
```

---

## Rollback Triggers

### Error Rate Spike

**Trigger:** Error rate increases by 150% or more

```
Example:
  Baseline: 0.8% error rate
  Current:  2.1% error rate
  Change:   (2.1 - 0.8) / 0.8 = 162% increase → SPIKE

Severity:
  Baseline 0.8% → Current 2.1% = HIGH
  → Confidence: 95%
  → Action: Rollback immediately
```

### Latency Degradation

**Trigger:** p95 latency increases by 50% or more

```
Example:
  Baseline: 150ms p95
  Current:  300ms p95
  Change:   (300 - 150) / 150 = 100% increase → SPIKE

Severity:
  Baseline 150ms → Current 300ms = MEDIUM-HIGH
  → Confidence: 85%
  → Action: Investigate, may rollback if trend continues
```

### Critical Errors

**Trigger:** Specific error patterns detected (e.g., database connection failures)

```
Example:
  10 "connection timeout" errors in 1 minute
  → CRITICAL_ERROR detected
  → Severity: CRITICAL
  → Confidence: 100%
  → Action: Immediate rollback
```

### Health Check Failures

**Trigger:** /health endpoint returns non-200

```
Endpoint: GET /health
Success: {"status": "ok", "db": true, "personas": 495}
Failure: {"status": "error", "db": false}

Failure detection:
  3 consecutive health check failures
  → HEALTH_CHECK_FAILED
  → Severity: CRITICAL
  → Action: Immediate rollback
```

---

## Configuration

### Default Policy

```json
{
  "enabled": true,
  "error_rate_threshold_percent": 2.0,
  "latency_threshold_ms": 500,
  "window_minutes": 5,
  "min_samples": 100,
  "cooldown_minutes": 15,
  "require_approval": false,
  "max_rollbacks_per_hour": 3
}
```

### Configuration Options

| Option | Default | Range | Meaning |
|--------|---------|-------|---------|
| `enabled` | true | bool | Enable/disable automatic rollback |
| `error_rate_threshold_percent` | 2.0 | 0.1-10 | Alert if error rate exceeds this % |
| `latency_threshold_ms` | 500 | 100-5000 | Alert if p95 latency exceeds this |
| `window_minutes` | 5 | 1-60 | Look-back window for metrics |
| `min_samples` | 100 | 10-1000 | Minimum samples before decision |
| `cooldown_minutes` | 15 | 5-60 | Prevent consecutive rollbacks |
| `require_approval` | false | bool | Manual approval required |
| `max_rollbacks_per_hour` | 3 | 1-10 | Max rollbacks in 60 min window |

### Example Configurations

**Conservative (Production):**
```json
{
  "enabled": true,
  "error_rate_threshold_percent": 1.0,
  "latency_threshold_ms": 300,
  "window_minutes": 10,
  "min_samples": 200,
  "cooldown_minutes": 30,
  "require_approval": true,
  "max_rollbacks_per_hour": 2
}
```

**Aggressive (Staging):**
```json
{
  "enabled": true,
  "error_rate_threshold_percent": 5.0,
  "latency_threshold_ms": 1000,
  "window_minutes": 2,
  "min_samples": 50,
  "cooldown_minutes": 5,
  "require_approval": false,
  "max_rollbacks_per_hour": 10
}
```

---

## API Reference

### Get Policy

```
GET /rollback/policy
```

**Response:**
```json
{
  "enabled": true,
  "error_rate_threshold_percent": 2.0,
  "latency_threshold_ms": 500,
  "window_minutes": 5,
  "min_samples": 100,
  "cooldown_minutes": 15,
  "require_approval": false,
  "max_rollbacks_per_hour": 3
}
```

### Update Policy

```
PATCH /rollback/policy
```

**Request:**
```json
{
  "enabled": true,
  "error_rate_threshold_percent": 3.0,
  "cooldown_minutes": 20
}
```

### Evaluate Rollback

```
POST /rollback/evaluate
```

**Request:**
```json
{
  "current_version": "1.2.3",
  "previous_version": "1.2.2",
  "error_rate_current": 5.2,
  "error_rate_baseline": 0.8,
  "latency_current_ms": 450,
  "latency_baseline_ms": 150,
  "sample_count": 250,
  "critical_errors": []
}
```

**Response:**
```json
{
  "should_rollback": true,
  "severity": "high",
  "confidence": 0.95,
  "explanation": "Error rate spiked by 550% (now 5.2%)",
  "estimated_recovery_seconds": 120,
  "recommended_action": "Investigate recent code changes",
  "can_execute_now": true,
  "alert": {
    "title": "🚨 Automatic Rollback Triggered",
    "severity": "HIGH",
    "from_version": "1.2.3",
    "to_version": "1.2.2",
    "explanation": "Error rate spiked by 550%"
  }
}
```

### Execute Rollback

```
POST /rollback/execute
```

**Request:**
```json
{
  "from_version": "1.2.3",
  "to_version": "1.2.2",
  "reason": "error_rate_spike"
}
```

**Response (Immediate):**
```json
{
  "status": "in_progress",
  "rollback_id": "rollback_abc123",
  "message": "Rollback initiated"
}
```

**Response (With Approval Required):**
```json
{
  "status": "pending_approval",
  "rollback_id": "rollback_abc123",
  "message": "Approval required for rollback",
  "approval_endpoint": "/rollback/rollback_abc123/approve"
}
```

### Get History

```
GET /rollback/history?limit=50
```

**Response:**
```json
{
  "total": 5,
  "rollbacks": [
    {
      "id": "rollback_abc123",
      "from_version": "1.2.3",
      "to_version": "1.2.2",
      "reason": "error_rate_spike",
      "status": "completed",
      "initiated_at": "2024-06-10T15:30:00Z",
      "completed_at": "2024-06-10T15:32:00Z",
      "details": {
        "error_rate_baseline": 0.8,
        "error_rate_current": 5.2
      }
    }
  ]
}
```

---

## GitHub Actions Integration

### Automated Rollback Workflow

Create `.github/workflows/auto-rollback.yml`:

```yaml
name: Auto-Rollback Monitoring (H94)

on:
  schedule:
    # Check every minute for issues
    - cron: '* * * * *'
  workflow_dispatch:

jobs:
  check-and-rollback:
    name: Monitor & Auto-Rollback
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Get current metrics
        id: metrics
        run: |
          ERROR_RATE=$(curl -s https://api.persona-hub.com/performance/metrics \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-API-Key: ${{ secrets.API_KEY }}" \
            ?metric_type=error_rate_percent&hours=1 | jq '.metrics[].value | add / length')
          
          LATENCY=$(curl -s https://api.persona-hub.com/performance/metrics \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-API-Key: ${{ secrets.API_KEY }}" \
            ?metric_type=response_time_ms&hours=1 | jq '.metrics[].value | sort | .[length*0.95]')
          
          echo "error_rate=$ERROR_RATE" >> $GITHUB_OUTPUT
          echo "latency=$LATENCY" >> $GITHUB_OUTPUT

      - name: Evaluate rollback decision
        id: evaluate
        run: |
          DECISION=$(curl -s -X POST https://api.persona-hub.com/rollback/evaluate \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-API-Key: ${{ secrets.API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{
              "current_version": "${{ github.ref }}",
              "previous_version": "main",
              "error_rate_current": ${{ steps.metrics.outputs.error_rate }},
              "error_rate_baseline": 0.8,
              "latency_current_ms": ${{ steps.metrics.outputs.latency }},
              "latency_baseline_ms": 150
            }')
          
          echo "$DECISION" > decision.json
          echo "should_rollback=$(echo $DECISION | jq '.should_rollback')" >> $GITHUB_OUTPUT
          echo "severity=$(echo $DECISION | jq -r '.severity')" >> $GITHUB_OUTPUT

      - name: Trigger rollback
        if: steps.evaluate.outputs.should_rollback == 'true'
        run: |
          ROLLBACK=$(curl -s -X POST https://api.persona-hub.com/rollback/execute \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-API-Key: ${{ secrets.API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{
              "from_version": "${{ github.ref }}",
              "to_version": "main",
              "reason": "automated_detection"
            }')
          
          echo "Rollback initiated:"
          echo "$ROLLBACK" | jq '.'

      - name: Notify team
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              text: '${{ steps.evaluate.outputs.should_rollback == "true" ? "🚨 AUTO-ROLLBACK TRIGGERED" : "✅ Metrics OK" }}',
              blocks: [
                {
                  type: 'section',
                  text: {
                    type: 'mrkdwn',
                    text: '*Automatic Rollback Check*\n\nError Rate: ${{ steps.metrics.outputs.error_rate }}%\nLatency: ${{ steps.metrics.outputs.latency }}ms\nDecision: ${{ steps.evaluate.outputs.severity }}'
                  }
                }
              ]
            }
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Examples

### Example 1: Auto-Rollback on Error Spike

```bash
# Deployment goes live at 2:00 PM
git push origin main

# 2:15 PM - Error rate spikes to 4.2% (was 0.8%)
# System automatically:
# 1. Detects spike (4.2 vs 0.8 = 425% increase)
# 2. Evaluates: severity=HIGH, confidence=98%
# 3. Decides: ROLLBACK
# 4. Executes: Deploy previous version
# 5. Verifies: Error rate drops back to 0.8%
# 6. Notifies: Team via Slack

curl -X POST https://api.persona-hub.com/rollback/execute \
  -H "X-API-Key: prs_..." \
  -d '{
    "from_version": "1.2.3",
    "to_version": "1.2.2",
    "reason": "error_rate_spike"
  }'

# Response:
# {
#   "status": "in_progress",
#   "estimated_recovery_seconds": 120
# }

# 2:17 PM - Metrics verify rollback successful
# Error rate: 0.8% ✅
# Latency: 150ms ✅
# Status: RECOVERED
```

### Example 2: Manual Approval Workflow

```bash
# Production deployment with strict policy
policy.require_approval = true

# Potential issue detected
curl -X POST https://api.persona-hub.com/rollback/evaluate \
  -H "X-API-Key: prs_..." \
  -d '{ "error_rate_current": 3.2, ... }'

# Response: should_rollback=true, but pending_approval

# Team gets Slack alert with approval link
# On-call engineer reviews metrics
# Approves rollback

curl -X POST https://api.persona-hub.com/rollback/rollback_abc123/approve \
  -H "X-API-Key: prs_..." \
  -d '{ "approval_token": "token_xyz" }'

# Rollback executes immediately
```

### Example 3: Prevent Rollback Loops

```
15:00 - Deploy v1.2.3 (has bug)
15:02 - Error rate spikes, auto-rollback to v1.2.2
15:04 - Rollback completed

15:15 - Deploy v1.2.4 (different fix)
15:17 - Different error appears
15:18 - System wants to rollback, but...
        cooldown period in effect (15 min)
        → BLOCKED: "Rollback in cooldown period"

Team is alerted: "Cooldown active, manual intervention needed"
On-call engineer investigates v1.2.4
```

---

## Safety Mechanisms

### Cooldown Period

**Purpose:** Prevent rollback loops (bad deploy → rollback → re-deploy → fail again)

```
Cooldown: 15 minutes (default, configurable)

Timeline:
  15:00 - Rollback #1 completes
  15:15 - Can rollback again
  15:14 - Cannot rollback (cooldown active)

Protection:
  - Stops thrashing between versions
  - Allows time for investigation
  - Forces manual intervention
```

### Max Rollbacks Per Hour

**Purpose:** Prevent excessive rollbacks that indicate deeper problems

```
Max per hour: 3 (default, configurable)

Timeline:
  15:00 - Rollback #1 completes
  15:05 - Rollback #2 completes
  15:10 - Rollback #3 completes
  15:12 - Rollback #4 would trigger, but...
          max_rollbacks_per_hour exceeded
          → BLOCKED: "Max rollbacks exceeded"

Alert: "Multiple rollbacks in 1 hour - emergency investigation needed"
```

### Minimum Sample Size

**Purpose:** Don't make decisions on noise/incomplete data

```
Min samples: 100 (default, configurable)

Scenario:
  - Deploy at 3:00 PM
  - Only 15 requests processed in 1 min
  - Error rate looks high (3/15 = 20%)
  - But too few samples
  - → WAIT for more data

After 10 minutes:
  - 1000 requests processed
  - Error rate: 0.9%
  - Sufficient confidence
  - → OK, continue monitoring
```

### Manual Approval Option

**Purpose:** Give teams ultimate control over production

```
Configuration:
  require_approval: true

Flow:
  1. Error detected, rollback evaluated
  2. Alert sent: "Approval needed, link: ..."
  3. Engineer gets 5 minutes to approve
  4. If approved: Rollback executes
  5. If timeout: Manual intervention required
```

---

## Incident Response

### Scenario 1: Auto-Rollback Successful

```
15:00 - Deploy v1.2.3
15:02 - Error spike detected
15:02 - Auto-rollback initiated
15:04 - v1.2.2 deployed and healthy
15:05 - Metrics verify recovery
15:05 - Team notified: "Rollback successful, investigating root cause"

Investigation:
  - Review v1.2.3 changes
  - Identify database query regression
  - Develop fix in v1.2.4
  - Test thoroughly before re-deploy
```

### Scenario 2: Rollback Blocked by Cooldown

```
15:00 - Deploy v1.2.3 (has bug A)
15:02 - Auto-rollback to v1.2.2
15:04 - Rollback completes

15:15 - Deploy v1.2.4 (different code, still has bug A)
15:17 - Error spike, but cooldown active
15:17 - Rollback BLOCKED: "Cooldown in effect (until 15:19)"
15:17 - Alert: "Deployment issue detected, manual action needed"

On-call response:
  - Acknowledge alert
  - Investigate v1.2.4 changes
  - If critical: git revert + manual push
  - If manageable: Wait until cooldown expires
```

### Scenario 3: Excessive Rollback Loop

```
14:50 - Deploy v1.2.0 (has issue)
14:52 - Rollback #1: back to v1.1.9
14:57 - Deploy v1.2.1 (same issue)
14:59 - Rollback #2: back to v1.1.9
15:04 - Deploy v1.2.2 (same issue)
15:06 - Rollback #3: back to v1.1.9
15:08 - Deploy v1.2.3 (same issue)
15:10 - Rollback #4 BLOCKED: "Max rollbacks/hour exceeded (3/3)"

Emergency response:
  - PagerDuty escalation
  - Disable auto-rollback
  - Manual revert to stable v1.1.9
  - Post-incident review
```

---

## Best Practices

### 1. Tune Thresholds Conservatively

```
❌ Too aggressive:
  error_rate_threshold: 0.1%
  → False positives, unnecessary rollbacks

✅ Conservative:
  error_rate_threshold: 2.0%
  → Real issues only, high confidence

Adjustment process:
  Week 1: 2.0% (conservative)
  Week 2: Monitor false positive rate
  Week 3: Adjust based on patterns
```

### 2. Use Manual Approval in Production

```
❌ Auto-rollback only:
  require_approval: false
  → No chance for human judgment

✅ With approval:
  require_approval: true
  → Team can investigate before rollback
  → Override if needed
```

### 3. Monitor Rollback Frequency

```
Healthy system:
  < 1 rollback per month
  → Deployments are stable

Warning signs:
  > 1 rollback per week
  → Investigation needed
  → Code quality issue?
  → Testing gaps?
```

### 4. Test Rollback Process

```
Monthly drill:
  1. Trigger manual rollback
  2. Verify deployment completes
  3. Verify metrics restore
  4. Document any issues
  5. Update procedures
```

---

## References

- [Canary Deployments](CANARY_DEPLOYMENTS.md)
- [Performance Regression Detection](PERFORMANCE_METRICS.md)
- [Feature Flags](FEATURE_FLAGS.md)
- [CI/CD Setup](CI_CD_SETUP.md)

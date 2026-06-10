# Canary Deployments (H91)

**Strategy:** Progressive rollout with automatic rollback on error detection  
**Traffic Shift:** 10% → 50% → 100% over ~8 minutes  
**Risk Level:** ⚠️ Low (isolated to 10% initially)  
**Rollback Time:** < 2 minutes (automatic)

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Architecture](#architecture)
4. [Setup & Configuration](#setup--configuration)
5. [Deployment Flow](#deployment-flow)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Overview

**Canary deployments** reduce deployment risk by:
1. **Gradual rollout** — New version receives small percentage of traffic first (10%)
2. **Automated monitoring** — CloudWatch metrics checked every 5 minutes
3. **Progressive shift** — If healthy, traffic increases: 10% → 50% → 100%
4. **Automatic rollback** — If error rate spikes, previous version restored immediately

**Benefits:**
- ✅ Detect issues affecting only 10% of users (not 100%)
- ✅ Quick automatic recovery if problems found
- ✅ Confidence to deploy multiple times per day
- ✅ Soft launch of new features to subset of users
- ✅ A/B testing opportunities (stable vs. canary)

**Trade-offs:**
- ⚠️ Slightly longer deployment window (~8 min vs 5 min)
- ⚠️ Requires dual infrastructure (stable + canary services)
- ⚠️ Increased monitoring and operational overhead

---

## How It Works

### Traffic Shifting Strategy

```
Time 0: Deploy new image to canary service
        ┌─────────────────────────────────┐
        │ Stable (v1.0.0) ████████████████ 100%
        │ Canary  (v1.1.0)                 0%
        └─────────────────────────────────┘

Time 1-5: Monitor canary at 10% traffic
        ┌─────────────────────────────────┐
        │ Stable (v1.0.0) ██████████████   90%
        │ Canary  (v1.1.0) ██               10%
        │ 📊 Check metrics: error rate, latency
        └─────────────────────────────────┘

Time 5-8: If healthy, shift to 50%
        ┌─────────────────────────────────┐
        │ Stable (v1.0.0) ███████░░░░░░░░░ 50%
        │ Canary  (v1.1.0) ███████░░░░░░░░░ 50%
        │ 📊 Re-check metrics
        └─────────────────────────────────┘

Time 8-10: If still healthy, shift to 100%
        ┌─────────────────────────────────┐
        │ Stable (v1.0.0)                   0%
        │ Canary  (v1.1.0) ████████████████ 100%
        │ ✅ Deployment complete
        └─────────────────────────────────┘

If error spike detected at any point:
        ┌─────────────────────────────────┐
        │ Stable (v1.0.0) ████████████████ 100%
        │ Canary  (v1.1.0)                  0%
        │ 🔄 Auto-rollback in < 2 minutes
        └─────────────────────────────────┘
```

### Health Checks

**Metrics monitored:**
| Metric | Threshold | Action |
|--------|-----------|--------|
| HTTP 5xx errors | > 5 in 5-min window | Stop, rollback |
| Response time p95 | > 2 seconds | Stop, rollback |
| Request rate | Gradual increase | Automatic |

---

## Architecture

### Infrastructure Components

```
┌────────────────────────────────────────────────────────┐
│ Application Load Balancer (ALB)                        │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Weight-Based Routing Rule                         │  │
│ │ - Stable: 90% (or 50%, or 0%)                    │  │
│ │ - Canary: 10% (or 50%, or 100%)                  │  │
│ │ Dynamic updates via GitHub Actions               │  │
│ └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
         │                          │
    (90% traffic)              (10% traffic)
         │                          │
┌────────▼──────────┐      ┌────────▼──────────┐
│ Stable Service    │      │ Canary Service    │
│ persona-hub       │      │ persona-hub-canary│
│ ┌──────────────┐  │      │ ┌──────────────┐  │
│ │ Task v1.0.0  │  │      │ │ Task v1.1.0  │  │
│ │ (2-5 tasks)  │  │      │ │ (2-5 tasks)  │  │
│ └──────────────┘  │      │ └──────────────┘  │
└───────────────────┘      └───────────────────┘
         │                          │
         └──────────────┬───────────┘
                        │
                   PostgreSQL
                   (Shared DB)
                   
        CloudWatch Metrics
        ├─ HTTPCode_Target_5XX_Count
        ├─ TargetResponseTime
        ├─ RequestCount
        └─ TargetConnectionCount
        
        CloudWatch Alarms
        ├─ persona-hub-canary-high-errors
        ├─ persona-hub-canary-high-latency
        └─ (triggers SNS → Slack/PagerDuty)
```

### ECS Task Definitions

**Stable Service:**
- Task definition: `persona-hub:latest` (e.g., v1.0.0)
- Desired count: 2 (minimum)
- Max: 5 (auto-scaling)

**Canary Service:**
- Task definition: `persona-hub:canary` (new version, e.g., v1.1.0)
- Desired count: 2 (minimum)
- Max: 5 (auto-scaling)
- Same task definition as stable initially, updated on deploy

---

## Setup & Configuration

### Step 1: Create Canary Infrastructure

```bash
# 1. Set environment variables
export CLUSTER_NAME="persona-hub-prod"
export VPC_ID="vpc-xxxxx"
export SUBNET_IDS="subnet-xxxxx,subnet-yyyyy"
export SECURITY_GROUP_ID="sg-xxxxx"

# 2. Run setup script (requires AWS CLI configured)
chmod +x scripts/setup-canary-infrastructure.sh
./scripts/setup-canary-infrastructure.sh

# Output:
# ✅ Canary target group created
# ✅ Canary ECS service created
# ✅ ALB rule created (90% stable, 10% canary)
# ✅ CloudWatch alarms created
# ✅ Auto-scaling configured
```

### Step 2: Configure GitHub Actions Secrets

```bash
# Store AWS role ARN for OIDC authentication
gh secret set AWS_ROLE_ARN \
  --body "arn:aws:iam::123456789:role/PersonaHubGitHubActionsRole"

# Store ALB rule ARN for traffic shifting
gh secret set ALB_RULE_ARN \
  --body "arn:aws:elasticloadbalancing:us-east-1:123456789:listener-rule/app/persona-hub-alb/50dc6c495c0c9ebc/listener/50dc6c495c1fcfbe/e0700e6c3cd97fd8"

# Verify secrets stored
gh secret list
# AWS_ROLE_ARN
# ALB_RULE_ARN
```

### Step 3: Enable Workflow

```bash
# Canary deployment workflow is automatically triggered on:
# 1. git push origin main
# 2. workflow dispatch (manual trigger)

# Manual trigger example:
gh workflow run canary-deploy.yml \
  --ref main \
  -f canary_percent=10

# Check workflow status
gh run list --workflow=canary-deploy.yml --limit=5
```

---

## Deployment Flow

### Automatic Deployment (on git push main)

```
[Developer commits]
       ↓
[git push origin main]
       ↓
[GitHub Actions triggered]
       ├─ build-image: Docker image created & pushed
       └─ wait for completion
       ↓
[canary-deploy]
       ├─ Get current task definition
       ├─ Register new task definition with new image
       ├─ Update canary service with new task definition
       ├─ Wait for service to stabilize
       └─ Verify canary service running
       ↓
[monitor-canary (5 minutes)]
       ├─ Wait 5 minutes for traffic/metrics to stabilize
       ├─ Collect error rate from CloudWatch
       ├─ Collect latency from CloudWatch
       ├─ Evaluate health (error_rate < 5, latency < 2s)
       └─ PASS → continue, FAIL → rollback
       ↓
[progressive-rollout (if monitoring passes)]
       ├─ Shift ALB rule to 50% traffic
       ├─ Wait 3 minutes, check metrics again
       ├─ If healthy, shift ALB rule to 100%
       ├─ Update main service task definition
       ├─ Wait for main service to stabilize
       └─ ✅ Deployment complete
       ↓
[rollback (if monitoring fails)]
       ├─ Stop canary service (desired_count = 0)
       ├─ Revert ALB rule to 100% stable
       └─ 🔄 Rolled back in < 2 minutes
       ↓
[notify-success or notify-rollback]
       └─ Slack message with status
```

### Manual Deployment (Workflow Dispatch)

```bash
# Trigger manually with custom canary percentage
gh workflow run canary-deploy.yml \
  --ref main \
  -f canary_percent=20

# Watch workflow progress
gh run watch
```

---

## Monitoring & Alerts

### CloudWatch Dashboard

**View canary metrics in real-time:**
```bash
# Open AWS CloudWatch Console
aws cloudwatch get-dashboard --dashboard-name PersonaHubCanary

# Or via AWS Console:
# CloudWatch → Dashboards → PersonaHubCanary
```

**Metrics displayed:**
- Error rate (5xx) — Stable vs Canary
- Response latency (avg, p95, p99) — Stable vs Canary
- Request rate — Canary traffic percentage
- Target health — Number of healthy tasks

### CloudWatch Alarms

**Automatic alerts configured:**

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| `persona-hub-canary-high-errors` | 5xx count | > 10 in 5 min | SNS → Slack/PagerDuty |
| `persona-hub-canary-high-latency` | Response time | > 2s avg | SNS → Slack/PagerDuty |

**Slack Notification Example:**
```
❌ CloudWatch Alarm: persona-hub-canary-high-errors
   Threshold: 10 errors in 5 minutes
   Current: 15 errors
   
   Action: Automatic rollback initiated
   Status: Canary service stopped, traffic reverted to stable
   
   Time: 2024-06-10 14:35 UTC
   View: https://console.aws.amazon.com/cloudwatch
```

### Manual Monitoring

```bash
# Check canary service status
aws ecs describe-services \
  --cluster persona-hub-prod \
  --services persona-hub-canary \
  --query 'services[0].[serviceName,status,runningCount,desiredCount]'

# View canary task logs
aws logs tail /ecs/persona-hub --follow --filter-pattern canary

# Get metrics (last 10 minutes)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=TargetGroup,Value=targetgroup/persona-hub-canary/abc123 \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum,Average
```

---

## Rollback Procedures

### Automatic Rollback (Triggered by Workflow)

**Triggered if:**
- Error rate > 5 errors in 5-minute window
- Response latency > 2 seconds
- Health check fails

**Automatic actions:**
1. ✅ Stop canary service (desired_count = 0)
2. ✅ Revert ALB rule to 100% stable traffic
3. ✅ Send Slack notification
4. ✅ Deployment marked as failed

**Time to recovery:** < 2 minutes (no manual intervention required)

### Manual Rollback

**If automatic rollback fails or issues detected later:**

```bash
# 1. Stop canary service
aws ecs update-service \
  --cluster persona-hub-prod \
  --service persona-hub-canary \
  --desired-count 0

# 2. Revert ALB to 100% stable
aws elbv2 modify-rule \
  --rule-arn arn:aws:elasticloadbalancing:... \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/persona-hub-stable

# 3. Verify stable service is receiving 100% traffic
curl https://api.persona-hub.com/health
# Response: {"status": "ok", "version": "1.0.0"}

# 4. Notify team
echo "Manual rollback completed" | mail -s "Rollback" team@persona-hub.com
```

### Database Rollback (if needed)

```bash
# If database changes caused issues:
# 1. Create RDS snapshot before each deployment
# 2. If rollback needed, restore from snapshot:

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier persona-hub-prod-restored \
  --db-snapshot-identifier persona-hub-prod-pre-deployment

# 3. Update application to point to restored DB
# 4. Run Alembic downgrade if migrations were breaking
alembic downgrade -1
```

---

## Troubleshooting

### Issue: Canary Service Fails to Start

```bash
# 1. Check task logs
aws logs tail /ecs/persona-hub --filter-pattern "persona-hub-canary" --follow

# 2. Describe service
aws ecs describe-services \
  --cluster persona-hub-prod \
  --services persona-hub-canary \
  --query 'services[0].[taskDefinition,runningCount,desiredCount,deployments]'

# 3. Check task definition
aws ecs describe-task-definition \
  --task-definition persona-hub:latest \
  --query 'taskDefinition.[containerDefinitions[0].image,memory,cpu]'

# 4. Common causes:
# - Image not found in registry: docker push <image>
# - Insufficient memory: increase task memory (ECS)
# - Port conflict: check ALB target group
# - Security group: verify port 8000 allowed inbound
```

### Issue: Canary Service Running But Not Receiving Traffic

```bash
# 1. Check ALB rule
aws elbv2 describe-rules \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --query 'Rules[?Priority==`1`].Actions'

# 2. Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/persona-hub-canary

# 3. If targets unhealthy:
# - Check security group allows ALB → ECS traffic
# - Verify health check path: /health
# - Check application logs for errors
```

### Issue: Canary Metrics Not Appearing in CloudWatch

```bash
# 1. Verify ALB is properly configured
aws elbv2 describe-load-balancers --names persona-hub-alb

# 2. Check target group has healthy targets
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/persona-hub-canary

# 3. Manually send traffic to canary
curl -H "Host: api.persona-hub.com" \
  http://persona-hub-alb-xxx.us-east-1.elb.amazonaws.com/health

# 4. If CloudWatch still empty, metrics may take 5 minutes to appear
```

### Issue: Workflow Stuck During Traffic Shift

```bash
# 1. Check GitHub Actions logs
gh run view <run-id> --log

# 2. Common causes:
# - ALB rule ARN incorrect in GitHub secret
# - AWS credentials expired
# - ECS service scaling up/down (wait for stability)

# 3. Manual intervention:
# - Revert ALB rule manually
# - Restart workflow: gh run rerun <run-id>
```

---

## Rollback Checklist

**If issues detected after deployment:**

```
☐ Check CloudWatch dashboard for error spike
☐ Verify issue is in canary (not other system)
☐ Collect logs from last 5 minutes
☐ Take screenshot of metrics
☐ Trigger manual rollback if auto-rollback didn't work
☐ Verify stable service is receiving 100% traffic
☐ Confirm health endpoint returns 200 OK
☐ Slack message to #deployments with status
☐ Schedule postmortem to investigate root cause
☐ Add test case to prevent regression
☐ Update deployment runbook if needed
```

---

## Advanced Usage

### Custom Canary Percentage

**Start with different traffic percentage (20% instead of 10%):**

```bash
gh workflow run canary-deploy.yml \
  --ref main \
  -f canary_percent=20
```

### Monitoring Thresholds Customization

**Adjust error rate threshold in `canary-deploy.yml`:**

```yaml
# Line ~200: Error rate check
if [ "${ERROR_RATE:-0}" -gt 5 ]; then
  # Change "5" to desired threshold (e.g., 10 for 10 errors/5min)
```

### Extended Monitoring Window

**Increase monitoring duration from 5 to 10 minutes:**

```yaml
# In monitor-canary job
- name: Wait for canary to stabilize
  run: |
    echo "⏳ Monitoring canary for 10 minutes..."
    for i in {1..10}; do  # Changed from 5 to 10
      echo "   [$i/10]..."
      sleep 60
    done
```

### Staged Rollout (10% → 25% → 50% → 100%)

**Modify progressive-rollout job to add intermediate stages:**

```yaml
- name: Shift to 25% traffic
  run: |
    # Update ALB rule with 25% weight
    
- name: Wait 2 minutes
  run: sleep 120

- name: Evaluate at 25%
  run: |
    # Check metrics again
```

---

## Metrics to Track

**Success metrics for canary deployments:**
| Metric | Target | Tool |
|--------|--------|------|
| Rollback rate | < 5% | GitHub Actions history |
| MTTR (Mean Time To Rollback) | < 2 min | CloudWatch logs |
| Error detection latency | < 5 min | Workflow execution time |
| Deployment frequency | Daily+ | GitHub releases |
| Time in canary phase | 5-10 min | Workflow execution time |

---

## References

- [AWS Deployment Strategies](https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/)
- [ECS Blue/Green Deployments](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-create-load-balancer.html)
- [CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/userguide/AlarmThatSendsEmail.html)
- [ALB Target Groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html)

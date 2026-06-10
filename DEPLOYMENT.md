# Deployment Guide

**Platform:** AWS ECS, RDS PostgreSQL, CloudFront CDN  
**Target:** Production environment (99.9% uptime SLA)  
**Estimated Deployment Time:** 45 minutes

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Health Verification](#health-verification)
5. [Post-Deployment](#post-deployment)
6. [Rollback Procedure](#rollback-procedure)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Code Quality

```bash
# 1. Run all tests locally
pytest tests/ --cov=api --cov-fail-under=75

# 2. Security scanning
gitleaks detect
bandit -r api/
safety check

# 3. Code formatting
black api/ tests/
isort api/ tests/
flake8 api/ tests/
mypy api/

# 4. Commit and push
git add .
git commit -m "Release: v1.2.3"
git push origin main
```

### GitHub Actions

```bash
# Wait for CI/CD pipeline to complete (5-10 minutes)
# Check: https://github.com/mk350174-cmd/persona-platform/actions

# All checks must be ✅ GREEN:
# ✅ ci-matrix.yml (Python 3.9-3.12 tests)
# ✅ security.yml (gitleaks, bandit, trivy)
# ✅ quality-gates.yml (flake8, mypy, black)
```

### Infrastructure Ready

```bash
# 1. Verify AWS credentials configured
aws sts get-caller-identity

# 2. Check RDS database accessible
psql $DATABASE_URL -c "SELECT version();"
# Output should show PostgreSQL 13+

# 3. Verify Stripe API keys
curl -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/account

# 4. Check Resend API credentials
curl -X POST https://api.resend.com/emails/verify \
  -H "Authorization: Bearer $RESEND_API_KEY"
```

### Create Release Tag

```bash
# Tag the release
git tag -a v1.2.3 -m "Production release v1.2.3"

# Push tag (triggers deploy workflow)
git push origin v1.2.3

# Verify workflow started
gh run list --limit=1  # Should show Deploy workflow
```

---

## Infrastructure Setup

### AWS Services Required

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **ECS** | Container orchestration | Fargate, 2–10 tasks |
| **ALB** | Load balancing | HTTPS, target groups |
| **RDS** | PostgreSQL database | Multi-AZ, automated backup |
| **RDS Proxy** | Connection pooling | 20-min idle timeout |
| **Secrets Manager** | Secret storage | Encryption at-rest |
| **S3** | Database backups | Versioning, lifecycle policies |
| **CloudWatch** | Logging | Log groups, retention 90 days |
| **Route 53** | DNS | Health checks, failover |
| **CloudFront** | CDN | Cache for static assets |

### Step 1: Create RDS Database

```bash
# 1a. Using AWS CLI
aws rds create-db-instance \
  --db-instance-identifier persona-hub-prod \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 13.12 \
  --allocated-storage 100 \
  --storage-type gp3 \
  --master-username persona_app \
  --master-user-password $(openssl rand -base64 32) \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name default \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --enable-multi-az \
  --storage-encrypted

# 1b. Or use CloudFormation template:
aws cloudformation create-stack \
  --stack-name persona-hub-db \
  --template-body file://cf-rds.yaml \
  --parameters ParameterKey=DBPassword,ParameterValue=XXXX
```

### Step 2: Store Secrets

```bash
# Store database password
aws secretsmanager create-secret \
  --name persona-hub/database-url \
  --secret-string "postgresql://persona_app:PASSWORD@persona-hub-prod.xxxxx.us-east-1.rds.amazonaws.com:5432/persona_hub"

# Store Stripe keys
aws secretsmanager create-secret \
  --name persona-hub/stripe-secret-key \
  --secret-string "sk_live_xxxxx"

aws secretsmanager create-secret \
  --name persona-hub/stripe-webhook-secret \
  --secret-string "whsec_xxxxx"

# Store Resend API key
aws secretsmanager create-secret \
  --name persona-hub/resend-api-key \
  --secret-string "re_xxxxx"
```

### Step 3: Create Application Load Balancer

```bash
# 1. Create ALB
aws elbv2 create-load-balancer \
  --name persona-hub-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-alb \
  --scheme internet-facing \
  --type application

# 2. Create target group
aws elbv2 create-target-group \
  --name persona-hub-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# 3. Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:...
```

### Step 4: Create ECS Cluster & Service

```bash
# 1. Create cluster
aws ecs create-cluster \
  --cluster-name persona-hub-prod \
  --settings name=containerInsights,value=enabled

# 2. Create task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Content of task-definition.json:
{
  "family": "persona-hub",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "persona-hub",
      "image": "ghcr.io/mk350174-cmd/persona-platform:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "BASE_URL",
          "value": "https://api.persona-hub.com"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:...:secret:persona-hub/database-url"
        },
        {
          "name": "STRIPE_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:...:secret:persona-hub/stripe-secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/persona-hub",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}

# 3. Create ECS service
aws ecs create-service \
  --cluster persona-hub-prod \
  --service-name persona-hub \
  --task-definition persona-hub \
  --desired-count 2 \
  --load-balancers targetGroupArn=arn:aws:...,containerName=persona-hub,containerPort=8000 \
  --network-configuration awsvpcConfiguration="{subnets=[subnet-xxxxx,subnet-yyyyy],securityGroups=[sg-ecs],assignPublicIp=DISABLED}" \
  --deployment-configuration maximumPercent=200,minimumHealthyPercent=100

# 4. Create auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/persona-hub-prod/persona-hub \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --policy-name persona-hub-scale-cpu \
  --service-namespace ecs \
  --resource-id service/persona-hub-prod/persona-hub \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

---

## Application Deployment

### Step 1: Run Database Migrations

```bash
# 1. Connect to RDS database
psql $DATABASE_URL

# 2. Run Alembic migrations (automated on container startup)
# OR manually:
alembic upgrade head

# 3. Verify tables created
\dt
# Should show: users, personas, purchases, subscriptions, invoices, wallet, audit_log, etc.

# 4. Check indexes
\di
# Should show 20+ indexes
```

### Step 2: Deploy Container

```bash
# 1. Build Docker image
docker build -t persona-hub:v1.2.3 .

# 2. Push to container registry (GitHub Container Registry)
docker tag persona-hub:v1.2.3 ghcr.io/mk350174-cmd/persona-platform:v1.2.3
docker push ghcr.io/mk350174-cmd/persona-platform:v1.2.3

# 3. Update ECS service to new image
aws ecs update-service \
  --cluster persona-hub-prod \
  --service persona-hub \
  --force-new-deployment

# 4. Wait for deployment to complete (5-10 minutes)
aws ecs wait services-stable \
  --cluster persona-hub-prod \
  --services persona-hub
```

### Step 3: Configure DNS

```bash
# 1. Create Route 53 record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://dns-change.json

# Content of dns-change.json:
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.persona-hub.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "persona-hub-alb-123456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}

# 2. Verify DNS propagation
nslookup api.persona-hub.com
# Should return ALB IP address
```

### Step 4: Configure HTTPS/TLS

```bash
# 1. Request SSL certificate (ACM)
aws acm request-certificate \
  --domain-name api.persona-hub.com \
  --subject-alternative-names "*.persona-hub.com" \
  --validation-method DNS

# 2. Validate certificate ownership (add DNS record)
# AWS ACM will provide CNAME record to add to Route 53

# 3. Update ALB to use certificate
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:...

# 4. Redirect HTTP to HTTPS
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"
```

---

## Health Verification

### Step 1: Test Endpoints

```bash
# 1. Health check (public, no auth)
curl https://api.persona-hub.com/health
# Expected: {"status": "ok", "version": "1.0.0", "db": true, "personas": 495}

# 2. Browse personas (public)
curl https://api.persona-hub.com/personas?limit=1
# Expected: JSON array with 1 persona

# 3. User registration
curl -X POST https://api.persona-hub.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "name": "Test User"
  }'
# Expected: {"api_key": "prs_...", "id": "usr_..."}

# 4. Login
curl -X POST https://api.persona-hub.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
# Expected: {"api_key": "prs_...", "user_id": "usr_..."}

# 5. Authenticated request
API_KEY="prs_..."
curl https://api.persona-hub.com/me \
  -H "X-API-Key: $API_KEY"
# Expected: User profile JSON
```

### Step 2: Check Database

```bash
# 1. Connect to production database
psql $DATABASE_URL

# 2. Verify user was created
SELECT COUNT(*) FROM users;
# Should return: 1 (or more if previous tests)

# 3. Check subscriptions available
SELECT COUNT(*) FROM personas;
# Should return: 495

# 4. Monitor audit log
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 5;
# Should show: USER_REGISTERED, USER_LOGGED_IN events
```

### Step 3: Load Testing

```bash
# Run light load test (50 concurrent users, 5 minutes)
cd tests
locust -f load_test_payments.py \
  --host https://api.persona-hub.com \
  --users 50 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# Expected metrics:
# - Response time p95: < 200ms
# - Success rate: 99%+
# - Error rate: < 1%
```

---

## Post-Deployment

### Slack Notification

```bash
# Notify team of successful deployment
curl -X POST $SLACK_WEBHOOK \
  -H "Content-Type: application/json" \
  -d '{
    "text": "✅ Production deployment successful",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Persona Platform v1.2.3 deployed to production*"
        }
      },
      {
        "type": "section",
        "fields": [
          {
            "type": "mrkdwn",
            "text": "*Deployment Time:*\nJune 10, 2024 14:30 UTC"
          },
          {
            "type": "mrkdwn",
            "text": "*API Endpoint:*\nhttps://api.persona-hub.com"
          },
          {
            "type": "mrkdwn",
            "text": "*Health:*\n✅ All checks passing"
          },
          {
            "type": "mrkdwn",
            "text": "*Load:*\n45 requests/sec"
          }
        ]
      }
    ]
  }'
```

### Update Documentation

```bash
# 1. Update API documentation with new version
# API_DOCS.md → Update version header

# 2. Create deployment log
cat > DEPLOYMENT_LOG.md << EOF
# Deployment Log

## v1.2.3 — June 10, 2024

**Time:** 14:00–14:45 UTC  
**Duration:** 45 minutes  
**Status:** ✅ Successful

### Changes:
- Add multi-Python CI/CD matrix (H87)
- Add auto-deployment workflow (H88)
- Add Slack/email notifications (H89)

### Metrics:
- Uptime: 100% (no downtime)
- Errors: 0
- Test coverage: 75.2%

### Rollback Status: None required
EOF

# 3. Commit deployment log
git add DEPLOYMENT_LOG.md
git commit -m "docs: log v1.2.3 production deployment"
git push origin main
```

### Monitor for Issues

```bash
# 1. Watch error rate for 1 hour
watch -n 10 'aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=persona-hub-alb \
  --start-time $(date -d "10 minutes ago" -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum'

# 2. Check application logs
aws logs tail /ecs/persona-hub --follow

# 3. Monitor database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;" # Every 30s

# 4. Check Stripe webhook delivery
curl -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/webhook_endpoints \
  | jq '.data[0].events_delivered'
```

---

## Rollback Procedure

**If issues detected in first 1 hour:**

### Option 1: Rollback to Previous Version

```bash
# 1. Stop current deployment
aws ecs update-service \
  --cluster persona-hub-prod \
  --service persona-hub \
  --desired-count 0

# 2. Verify service is stopped (30 seconds)
aws ecs describe-services \
  --cluster persona-hub-prod \
  --services persona-hub

# 3. Deploy previous image
aws ecs update-service \
  --cluster persona-hub-prod \
  --service persona-hub \
  --task-definition persona-hub:2  # Previous revision
  --desired-count 2 \
  --force-new-deployment

# 4. Wait for stabilization
aws ecs wait services-stable \
  --cluster persona-hub-prod \
  --services persona-hub

# 5. Verify health
curl https://api.persona-hub.com/health

# 6. Notify team
echo "Rolled back to previous version" | mail -s "Rollback" team@persona-hub.com
```

### Option 2: Roll Back Database

```bash
# 1. Create RDS snapshot before deployment
aws rds create-db-snapshot \
  --db-instance-identifier persona-hub-prod \
  --db-snapshot-identifier persona-hub-prod-pre-deployment

# 2. If database corruption detected, restore:
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier persona-hub-prod-restored \
  --db-snapshot-identifier persona-hub-prod-pre-deployment

# 3. Verify restored database
psql postgresql://persona_app:password@persona-hub-prod-restored.xxxx.us-east-1.rds.amazonaws.com:5432/persona_hub -c "SELECT COUNT(*) FROM users;"

# 4. If valid, swap endpoints (update Route 53, environment variables)
# 5. Decommission broken database
aws rds delete-db-instance \
  --db-instance-identifier persona-hub-prod \
  --skip-final-snapshot
```

---

## Monitoring & Alerts

### CloudWatch Dashboards

```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name PersonaHubProd \
  --dashboard-body file://dashboard.json
```

**Key Metrics to Monitor:**

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| CPU Usage | > 70% for 5 min | Scale up |
| Memory Usage | > 80% for 5 min | Scale up |
| Error Rate (5xx) | > 5% | PagerDuty page |
| Response Time (p95) | > 5s | Investigate |
| Database Connections | > 15/20 | Check for leak |
| Replication Lag | > 10s | Investigate RDS |

### PagerDuty Integration

```bash
# Configure SNS → PagerDuty
aws sns create-topic --name persona-hub-alerts

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789:persona-hub-alerts \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/...

# Attach alarm to topic
aws cloudwatch put-metric-alarm \
  --alarm-name persona-hub-high-error-rate \
  --alarm-description "Alert if error rate > 5%" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 25 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:persona-hub-alerts
```

---

## Troubleshooting

### Issue: Container Fails to Start

```bash
# 1. Check task logs
aws logs get-log-events \
  --log-group-name /ecs/persona-hub \
  --log-stream-name ecs/persona-hub/ab123456

# Common errors:
# - "ExitCode: 1" → Check environment variables, secrets
# - "OutOfMemory" → Increase task memory (ECS)
# - "Port already in use" → Previous task didn't stop

# 2. Verify secrets are accessible
aws secretsmanager get-secret-value \
  --secret-id persona-hub/database-url

# 3. Check task IAM role permissions
aws iam get-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerAccess
```

### Issue: Database Connection Timeout

```bash
# 1. Verify RDS security group
aws ec2 describe-security-groups \
  --group-ids sg-rds \
  --query 'SecurityGroups[0].IpPermissions'
# Should allow inbound on port 5432 from ECS security group

# 2. Test connection from ECS task
aws ecs execute-command \
  --cluster persona-hub-prod \
  --task <task-id> \
  --container persona-hub \
  --command "/bin/bash" \
  --interactive

# Inside container:
psql $DATABASE_URL -c "SELECT 1"

# 3. Check RDS availability
aws rds describe-db-instances \
  --db-instance-identifier persona-hub-prod \
  --query 'DBInstances[0].DBInstanceStatus'
# Should return "available"
```

### Issue: High Latency

```bash
# 1. Check database query performance
psql $DATABASE_URL << EOF
SELECT query, mean_time, max_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
EOF

# 2. Check for missing indexes
SELECT * FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC;

# 3. Analyze query plan
EXPLAIN ANALYZE
SELECT * FROM purchases WHERE user_id = 'usr_123';

# 4. Consider adding index
CREATE INDEX idx_purchases_user ON purchases(user_id);
ANALYZE purchases;
```

### Issue: Stripe Webhook Not Firing

```bash
# 1. Verify webhook registered in Stripe
curl -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/webhook_endpoints

# Should show persona-hub endpoint with status "enabled"

# 2. Check webhook delivery logs
curl -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/webhook_endpoints/we_xxx/attempts

# 3. Manually trigger test webhook
curl -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/webhook_endpoints/we_xxx/test_helpers/send_sample_event \
  -d "event=charge.succeeded"

# 4. Check application logs for webhook processing
aws logs filter-log-events \
  --log-group-name /ecs/persona-hub \
  --filter-pattern "webhook"
```

---

## Rollback Checklist

```bash
# Before rollback, collect diagnostics:
☐ Screenshot CloudWatch dashboard
☐ Export last 1 hour of logs: aws logs get-log-events --log-group-name /ecs/persona-hub
☐ Capture current error rate: aws cloudwatch get-metric-statistics
☐ Note affected users/requests
☐ Check Stripe dashboard for transaction state
☐ Verify database integrity: SELECT COUNT(*) FROM users;

# Rollback steps:
☐ Stop current deployment (set desired_count to 0)
☐ Deploy previous image
☐ Verify /health endpoint
☐ Monitor error rate for 15 minutes
☐ Run smoke tests
☐ Notify team on Slack

# Post-rollback:
☐ Document issue in incident report
☐ Schedule postmortem
☐ Add regression test to prevent recurrence
☐ Update deployment runbook
```

---

## Support

- **Emergency Hotline:** +1-xxx-xxx-xxxx
- **Slack:** #deployments channel
- **Email:** ops@persona-hub.com
- **Status Page:** https://status.persona-hub.com

**Deployment runbook:** This document  
**Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)  
**CI/CD:** [CI_CD_SETUP.md](CI_CD_SETUP.md)

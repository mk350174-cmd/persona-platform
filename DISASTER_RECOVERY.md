# Disaster Recovery & Backup Strategy — H97

**Purpose:** Comprehensive guide for database backup, disaster recovery, point-in-time recovery, and failover procedures.

**SLA Objectives:**
- **RTO (Recovery Time Objective):** 2 hours
- **RPO (Recovery Point Objective):** 15 minutes
- **Backup Retention:** 30 days
- **Testing:** Monthly dry-run, quarterly full failover test

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture & Strategy](#architecture--strategy)
3. [Setup & Configuration](#setup--configuration)
4. [Backup Procedures](#backup-procedures)
5. [Recovery Procedures](#recovery-procedures)
6. [Failover Testing](#failover-testing)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Troubleshooting](#troubleshooting)
9. [Runbook for On-Call Engineers](#runbook-for-on-call-engineers)

---

## Quick Start

### Manual Full Backup (Right Now)
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/persona_hub"
export BACKUP_S3_BUCKET="my-backup-bucket"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

./scripts/backup/pg_backup.sh
```

### Restore from Backup (Emergency Recovery)
```bash
# Restore from latest backup
./scripts/backup/pg_restore.sh latest persona_hub

# Restore from specific time
./scripts/backup/pg_restore.sh 2024-06-10T14-30-00Z persona_hub

# Verify restore succeeded
psql -h localhost -p 5432 -U persona -d persona_hub -c "SELECT COUNT(*) FROM users;"
```

### Rollback (If Recovery Fails)
```bash
./scripts/backup/pg_restore.sh --rollback
```

### Validate Latest Backup
```bash
./scripts/backup/validate_backup.sh latest
```

### Run Failover Drill
```bash
./scripts/backup/failover_test.sh --full
```

---

## Architecture & Strategy

### Backup Method

**Daily Full Backup:**
- Timestamp: 02:00 UTC (configurable)
- Tool: `pg_dump` (logical backup)
- Format: Plain SQL (human-readable)
- Compression: gzip (reduces size by 80–90%)
- Destination: S3 bucket with AES-256 encryption
- Retention: 30 days (older backups auto-deleted)

**Local Backup Staging:**
- Location: `/tmp/persona_backups/` (on backup container)
- Purpose: Intermediate storage before S3 upload
- Cleanup: Deleted after successful S3 upload
- Retention: 30 days (old local backups auto-purged)

**S3 Configuration:**
- Bucket: `persona-backups-prod` (or `BACKUP_S3_BUCKET` env var)
- Encryption: Server-side AES-256 (`--sse AES256`)
- Metadata tags: timestamp, database name, file size
- Lifecycle policy: Expire objects after 30 days

### Point-in-Time Recovery (PITR)

If PostgreSQL WAL archiving is enabled:
- Recover to any second within WAL retention window (e.g., 7 days)
- Restore from full backup + apply WAL files up to target timestamp
- Requires: `wal_level=replica` and archiving configured

If WAL archiving is NOT enabled (current setup):
- Can only recover to backup timestamps (daily)
- Lose up to 24 hours of data in worst case
- **Recommendation:** Enable WAL archiving for production

### Disaster Scenarios

| Scenario | Cause | Detection | Recovery |
|----------|-------|-----------|----------|
| **Data Corruption** | Query error, app bug | Application errors | Restore from backup (check all tables) |
| **Disk Failure** | Hardware failure | Connection refused | Restore to new disk, update DNS |
| **Ransomware** | Security breach | File encryption detected | Restore from backup (before attack timestamp) |
| **Accidental Delete** | Human error (DROP TABLE) | Missing data | PITR: restore to before delete |
| **Primary Database Down** | Infrastructure failure | Health check fails | Failover: switch to standby or restore |

---

## Setup & Configuration

### Prerequisites

**On Host Machine:**
- PostgreSQL client tools: `psql`, `pg_dump`, `createdb`, `dropdb`
- AWS CLI v2 with configured credentials
- Docker Compose (for container orchestration)
- Bash 4.0+ (macOS may need upgrade: `brew install bash`)

**AWS Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::persona-backups-prod",
        "arn:aws:s3:::persona-backups-prod/*"
      ]
    }
  ]
}
```

**PostgreSQL Version:**
- Minimum: PostgreSQL 12
- Recommended: PostgreSQL 16+ (latest stable)
- Backup compatibility: Forward/backward compatible with 2+ minor versions

### Docker Compose Setup

The backup service is included in `docker-compose.yml`:

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: persona_hub
    POSTGRES_USER: persona
    POSTGRES_PASSWORD: persona_dev_password
  volumes:
    - postgres_data:/var/lib/postgresql/data

backup:
  image: postgres:16-alpine
  volumes:
    - ./scripts/backup:/backup:ro
    - backup_data:/backups
  environment:
    DATABASE_URL: postgresql://persona:persona_dev_password@postgres:5432/persona_hub
    BACKUP_S3_BUCKET: ${BACKUP_S3_BUCKET}
    AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
    AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
  depends_on:
    postgres:
      condition: service_healthy
  # Cron jobs: 02:00 UTC daily backup, hourly validation
```

### Environment Configuration

Create/update `.env` file:

```bash
# PostgreSQL
POSTGRES_USER=persona
POSTGRES_PASSWORD=secure_random_password_here
DATABASE_URL=postgresql://persona:${POSTGRES_PASSWORD}@postgres:5432/persona_hub

# Backup
BACKUP_S3_BUCKET=persona-backups-prod
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
BACKUP_RETENTION_DAYS=30
```

**DO NOT** commit credentials to git. Use `.env.example` as template.

### Initial Setup Steps

```bash
# 1. Create .env from template
cp .env.example .env
# Edit .env with your values

# 2. Create S3 bucket
aws s3 mb s3://persona-backups-prod --region us-east-1

# 3. Enable S3 encryption
aws s3api put-bucket-encryption \
  --bucket persona-backups-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
    }]
  }'

# 4. Set S3 lifecycle policy (auto-delete after 30 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket persona-backups-prod \
  --lifecycle-configuration '{
    "Rules": [{
      "Id": "delete-old-backups",
      "Status": "Enabled",
      "Expiration": {"Days": 30},
      "Filter": {"Prefix": "persona_backup_"}
    }]
  }'

# 5. Start services
docker-compose up -d postgres
docker-compose up -d api

# 6. Start backup service
docker-compose up -d backup

# 7. Verify cron jobs
docker-compose logs backup | grep -i cron

# 8. Run initial backup
docker-compose exec backup /backup/pg_backup.sh

# 9. Verify backup in S3
aws s3 ls s3://persona-backups-prod/
```

---

## Backup Procedures

### Daily Automated Backup

**Schedule:** 02:00 UTC (daily)
**Duration:** 5–30 minutes (depends on database size)
**Location:** Backup container cron job

**Automatic Steps:**
1. Connect to PostgreSQL database
2. Run `pg_dump` with full schema + data
3. Compress with gzip
4. Upload to S3 with AES-256 encryption
5. Delete local copy
6. Log success/failure

**Monitoring:**
- Check logs: `docker-compose logs backup`
- Verify S3 upload: `aws s3 ls s3://persona-backups-prod/`
- GitHub Actions: Weekly health check (Sunday 10:00 UTC)

### Manual Backup (On-Demand)

If you need to backup immediately (before deployment, before major change):

```bash
# Set environment variables
export DATABASE_URL="postgresql://persona:password@postgres:5432/persona_hub"
export BACKUP_S3_BUCKET="persona-backups-prod"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

# Run backup script
./scripts/backup/pg_backup.sh

# Check result
ls -lh /tmp/persona_backups/
aws s3 ls s3://persona-backups-prod/
```

### Backup Validation

**Automatic (Hourly):**
```bash
./scripts/backup/validate_backup.sh latest
```

**Manual:**
```bash
./scripts/backup/validate_backup.sh 2024-06-10T14-30-00Z
```

**What it checks:**
- ✅ Gzip file integrity (not corrupted)
- ✅ File size > 1MB (not empty)
- ✅ Contains SQL keywords (CREATE, INSERT, DROP)
- ✅ S3 metadata readable
- ✅ Backup not older than 24 hours

---

## Recovery Procedures

### Scenario 1: Quick Recovery to Latest Backup (Emergency)

**Situation:** Database is corrupted or lost, need to restore ASAP.

**Time Required:** ~30 min to 2 hours (depends on data size)

**Steps:**

```bash
# 1. Verify backup exists
aws s3 ls s3://persona-backups-prod/ | tail -5

# 2. Download backup
aws s3 cp "s3://persona-backups-prod/persona_backup_TIMESTAMP.sql.gz" /tmp/backup.sql.gz

# 3. Verify backup integrity
gzip -t /tmp/backup.sql.gz  # Should return 0 (no error)

# 4. Create test database (optional but recommended)
psql -h localhost -p 5432 -U persona -d postgres \
  -c "CREATE DATABASE persona_hub_test;"

# 5. Restore to test database (verify first)
gunzip -c /tmp/backup.sql.gz | \
  psql -h localhost -p 5432 -U persona -d persona_hub_test

# 6. Verify test database
psql -h localhost -p 5432 -U persona -d persona_hub_test \
  -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM purchases;"

# 7. If test looks good, restore to production
gunzip -c /tmp/backup.sql.gz | \
  psql -h localhost -p 5432 -U persona -d persona_hub

# 8. Verify production database
psql -h localhost -p 5432 -U persona -d persona_hub \
  -c "SELECT * FROM users LIMIT 1;"

# 9. Drop test database
psql -h localhost -p 5432 -U persona -d postgres \
  -c "DROP DATABASE persona_hub_test;"

# 10. Cleanup
rm /tmp/backup.sql.gz
```

**Verification Checklist:**
- [ ] Can connect to database: `psql ... -c "SELECT 1"`
- [ ] Users table exists: `SELECT COUNT(*) FROM users`
- [ ] Data is recent: `SELECT MAX(created_at) FROM purchases`
- [ ] All tables present: `SELECT * FROM information_schema.tables`
- [ ] Application can connect: `curl http://localhost:8000/health`

### Scenario 2: Point-in-Time Recovery (Targeted)

**Situation:** Need to recover to a specific time (e.g., before accidental deletion happened at 14:30).

**Steps:**

```bash
# 1. Find backup before the target time
# (Assuming daily backups at 02:00 UTC)
# If incident at 2024-06-10T14:30:00Z, use backup from 2024-06-10T02:00:00Z

TIMESTAMP="2024-06-10T02-00-00Z"  # Format: YYYY-MM-DDTHH-MM-SSZ

# 2. Use recovery script
./scripts/backup/pg_restore.sh "$TIMESTAMP" persona_hub_recovered

# 3. Verify recovered database
psql -h localhost -p 5432 -U persona -d persona_hub_recovered \
  -c "SELECT COUNT(*) FROM users, MAX(created_at) FROM purchases;"

# 4. If satisfied, backup current (corrupted) and swap
psql -h localhost -p 5432 -U persona -d postgres \
  -c "ALTER DATABASE persona_hub RENAME TO persona_hub_corrupted;"

psql -h localhost -p 5432 -U persona -d postgres \
  -c "ALTER DATABASE persona_hub_recovered RENAME TO persona_hub;"

# 5. Restart application to re-establish connection
docker-compose restart api

# 6. Verify application
curl http://localhost:8000/health

# 7. Keep corrupted database for investigation (backup it before deleting)
pg_dump -h localhost -p 5432 -U persona -d persona_hub_corrupted > /backup/corrupted_$(date +%s).sql

psql -h localhost -p 5432 -U persona -d postgres \
  -c "DROP DATABASE persona_hub_corrupted;"
```

### Scenario 3: Full Failover to New Server

**Situation:** Server hardware is compromised, need to spin up completely new server.

**Steps:**

```bash
# 1. On NEW server, install prerequisites
apt-get update
apt-get install -y postgresql-client-16 awscli

# 2. Download latest backup from S3
aws s3 cp \
  "s3://persona-backups-prod/$(aws s3 ls s3://persona-backups-prod/ | tail -1 | awk '{print $NF}')" \
  /tmp/backup.sql.gz

# 3. Install PostgreSQL
apt-get install -y postgresql-16
systemctl start postgresql

# 4. Create database and user
sudo -u postgres createdb persona_hub
sudo -u postgres createuser persona
sudo -u postgres psql -c "ALTER USER persona WITH PASSWORD 'new_password';"

# 5. Restore backup
gunzip -c /tmp/backup.sql.gz | psql -U persona -d persona_hub

# 6. Verify restore
psql -U persona -d persona_hub -c "SELECT COUNT(*) FROM users;"

# 7. Update DNS to point to new server
# (Edit DNS records, update CNAME to new server IP)

# 8. Update application DATABASE_URL
# (Update .env and restart application)

# 9. Run smoke tests
curl http://new-server:8000/health
curl http://new-server:8000/personas -H "X-API-Key: test-key"

# 10. Celebrate! You're back online.
```

---

## Failover Testing

### Monthly Dry-Run Test

**Objective:** Verify recovery procedure works, measure RTO.

**Duration:** 1 hour, monthly (first Monday of each month)

**Procedure:**

```bash
# 1. Schedule test window (announce on Slack)
echo "🔔 BACKUP DRILL: 15:00-16:00 UTC — No production impact"

# 2. Run failover test script
./scripts/backup/failover_test.sh --full

# 3. Monitor output
# Expected:
# ✅ Recovery test START
# ✅ Database connectivity check passed
# ✅ Recovery completed successfully
# ✅ Data integrity verification passed
# ✅ Recovery test PASSED
# Recovery time: XXX seconds

# 4. Document results
# - Actual recovery time
# - Any errors or warnings
# - Database size at backup
# - Row counts (users, purchases, subscriptions)

# 5. Report to team
# - Slack message with results
# - GitHub issue if anything failed
# - Update RTO/RPO in this document if times changed
```

### Quarterly Full Failover Test

**Objective:** Complete end-to-end failover simulation, including application restart.

**Duration:** 2–3 hours, quarterly (Jan, Apr, Jul, Oct)

**Procedure:**

```bash
# 1. Notify team 1 week before
#    - Schedule maintenance window
#    - Brief stakeholders
#    - Identify backup on-call engineer

# 2. Take database backup before test
./scripts/backup/pg_backup.sh

# 3. Create test server (or use staging)
docker-compose -f docker-compose.test.yml up -d

# 4. Run restore on test server
./scripts/backup/pg_restore.sh latest test_persona_hub

# 5. Verify database connectivity
psql -h localhost -p 5432 -U persona -d test_persona_hub -c "SELECT 1"

# 6. Start application against test database
DATABASE_URL="postgresql://persona:password@localhost:5432/test_persona_hub" \
  docker-compose up -d api

# 7. Run smoke tests
curl http://localhost:8000/health
curl http://localhost:8000/personas?limit=5 -H "X-API-Key: test-key"

# 8. Simulate user traffic (10 requests)
for i in {1..10}; do
  curl -s http://localhost:8000/personas | jq '.personas[0].name' &
done
wait

# 9. Measure actual RTO from start to application ready
# Expected: < 2 hours
# - 10 min: download backup from S3
# - 20 min: decompress + restore to database
# - 10 min: verify + restart application
# - 10 min: smoke tests + verification

# 10. Document findings
# - Actual RTO (time from restore start to application ready)
# - Actual RPO (backup timestamp — how much data recovered)
# - Any issues encountered
# - Suggestions for improvement

# 11. Cleanup
docker-compose down
```

### Failed Test? Here's the Troubleshooting

**Issue: Cannot download backup from S3**
- Check AWS credentials in `.env`
- Verify S3 bucket name is correct
- Check bucket permissions: `aws s3 ls s3://persona-backups-prod/`
- If IAM issue: update AWS access key

**Issue: Restore fails (SQL syntax error)**
- Check backup file integrity: `gzip -t backup.sql.gz`
- Try restoring to fresh test database
- If persistent: check PostgreSQL version compatibility

**Issue: Recovery takes > 2 hours (exceeds RTO)**
- Database may have grown larger than expected
- Consider incremental backups or WAL archiving
- Test on newer hardware (more CPU/disk speed)

---

## Monitoring & Alerting

### Backup Health Monitoring

**GitHub Actions Workflow:** `.github/workflows/backup-health.yml`
- **Frequency:** Weekly (Sunday 10:00 UTC)
- **Checks:** Backup age, file integrity, S3 accessibility

**Alerting:**
- ✅ Success: Slack message (green)
- ❌ Failure: Slack message (red) + GitHub issue created

**Manual Check (anytime):**
```bash
./scripts/backup/validate_backup.sh latest
```

### Backup Age Monitoring

**Alert if:** Backup older than 24 hours

**Cause:** Backup container down, cron job failed, S3 upload failed

**Action:**
1. Check backup container logs: `docker-compose logs backup`
2. Check S3 bucket: `aws s3 ls s3://persona-backups-prod/`
3. Manually run backup: `./scripts/backup/pg_backup.sh`
4. If persistent, restart backup container: `docker-compose restart backup`

### Backup Size Monitoring

**Alert if:** Backup size decreased >20% from average

**Cause:** Data loss, accidental truncation, backup corruption

**Action:**
1. Compare with previous backups: `aws s3 ls s3://persona-backups-prod/ | sort`
2. Check database row count: `SELECT COUNT(*) FROM users, purchases, subscriptions;`
3. If suspiciously low, restore from prior backup

---

## Troubleshooting

### Common Issues & Solutions

#### Issue: `pg_dump: error: could not connect to database`

**Cause:** Database connection failed (wrong credentials, network issue, DB down)

**Solution:**
```bash
# Test connection manually
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1"

# If fails, check:
# - Database host/port correct?
# - User credentials correct?
# - Database exists?
# - Network connectivity to host?

# Verify DATABASE_URL format
echo $DATABASE_URL
# Expected: postgresql://user:password@host:port/dbname
```

#### Issue: `permission denied` when writing backup file

**Cause:** Backup directory not writable (file permissions issue)

**Solution:**
```bash
# Check directory permissions
ls -ld /tmp/persona_backups/

# Fix permissions
mkdir -p /tmp/persona_backups/
chmod 777 /tmp/persona_backups/

# Or in Docker:
docker-compose exec backup chmod 777 /backups/
```

#### Issue: S3 upload fails: `An error occurred (NoSuchBucket)`

**Cause:** S3 bucket doesn't exist or wrong name

**Solution:**
```bash
# List buckets
aws s3 ls

# Create bucket if missing
aws s3 mb s3://persona-backups-prod --region us-east-1

# Verify bucket name in .env
grep BACKUP_S3_BUCKET .env
```

#### Issue: S3 upload fails: `credentials not found`

**Cause:** AWS credentials not set in environment

**Solution:**
```bash
# Check credentials
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY

# Load from .env
set -a
source .env
set +a

# Or configure AWS CLI
aws configure
# Enter Access Key ID, Secret Access Key, region
```

#### Issue: Restore fails: `role "persona" does not exist`

**Cause:** PostgreSQL user not created

**Solution:**
```bash
# On target PostgreSQL server:
psql -U postgres -c "CREATE USER persona WITH PASSWORD 'password';"
psql -U postgres -c "ALTER USER persona CREATEDB;"
psql -U postgres -c "CREATE DATABASE persona_hub OWNER persona;"
```

#### Issue: Application still showing old data after restore

**Cause:** Application connected to old database or has cached connection

**Solution:**
```bash
# Restart application
docker-compose restart api

# Or force connection refresh
docker-compose down
docker-compose up -d api

# Verify application is connected to restored database
curl http://localhost:8000/health
```

---

## Runbook for On-Call Engineers

### Quick Reference (Laminated Card)

**BACKUP EMERGENCY PLAYBOOK**

**Step 1: Is the database down?**
```bash
psql -h $DB_HOST -U $DB_USER -d persona_hub -c "SELECT 1"
```
- If YES → Go to Step 3 (Restore)
- If NO → Go to Step 2 (Data Integrity)

**Step 2: Is the data corrupted?**
```bash
psql -h $DB_HOST -U $DB_USER -d persona_hub \
  -c "SELECT COUNT(*) FROM users, COUNT(*) FROM purchases"
```
- If counts look wrong → Go to Step 3 (Restore)
- If looks OK → Database is fine, investigate application issue

**Step 3: Restore from latest backup**
```bash
./scripts/backup/pg_restore.sh latest persona_hub
```
- Command will prompt for confirmation
- Wait for message: "Restore completed successfully"
- If ERROR → Go to Step 5 (Troubleshooting)

**Step 4: Verify restore**
```bash
psql -h $DB_HOST -U $DB_USER -d persona_hub \
  -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM purchases;"

curl http://localhost:8000/health
```
- If both look good → CRISIS OVER ✅
- If still broken → Go to Step 5 (Troubleshooting)

**Step 5: Rollback (if restore failed)**
```bash
./scripts/backup/pg_restore.sh --rollback
```
- This swaps back to previous database
- If that fails → you need help, call #ops-team on Slack

**Step 6: Contact on-call manager & document**
- Slack: #incident-response
- What happened?
- How long was it down?
- What actions were taken?
- Did backup/restore work?

---

### Detailed Runbook

**Situation: Database Unreachable / Corrupted**

**Estimated Recovery Time: 1–2 hours**

**1. ASSESS THE SITUATION (5 min)**
```bash
# Can you connect?
psql -h localhost -p 5432 -U persona -d persona_hub -c "SELECT NOW()"

# What error do you get?
# - "FATAL: database "persona_hub" does not exist" → Database deleted
# - "FATAL: could not connect to server" → Server down
# - "ERROR: relation "users" does not exist" → Schema missing
# - Hangs, no response → Server hung/unresponsive

# Check application logs
docker-compose logs api | tail -50
docker-compose logs postgres | tail -50

# Check disk space
df -h
```

**2. NOTIFY TEAM (2 min)**
- Post in #incident-response: "🔴 Database outage, starting recovery"
- Include: timestamp, error, estimated impact
- Set status page to "INVESTIGATING"

**3. CHECK BACKUP STATUS (3 min)**
```bash
# Do we have a good backup?
aws s3 ls s3://persona-backups-prod/ | tail -5

# Validate latest backup
./scripts/backup/validate_backup.sh latest
# Expected: "Status: VALID"
```

**4. STOP ACTIVE CONNECTIONS (2 min)**
```bash
# Disconnect application to avoid conflicts
docker-compose stop api

# If you need to keep it running:
psql -h localhost -U postgres -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'persona_hub';"
```

**5. RESTORE FROM BACKUP (30–60 min)**
```bash
# Option A: Latest backup (recommended for speed)
./scripts/backup/pg_restore.sh latest persona_hub

# Option B: Specific time (if you know when corruption started)
./scripts/backup/pg_restore.sh 2024-06-10T02-00-00Z persona_hub

# Monitor progress
docker logs -f $(docker-compose ps -q backup) 2>/dev/null || \
  tail -f /var/log/persona_restore.log
```

**6. VERIFY DATA (5 min)**
```bash
# Connect to restored database
psql -h localhost -U persona -d persona_hub

# Quick sanity checks
SELECT COUNT(*) FROM users;           -- Should be > 0
SELECT COUNT(*) FROM purchases;       -- Should be > 0
SELECT MAX(created_at) FROM users;    -- Should be recent
SELECT MAX(created_at) FROM purchases; -- Should be recent

# If any of these are 0 or very old:
# ❌ Something is wrong
# → Go to TROUBLESHOOTING section
# ✅ If all look good, continue to step 7
```

**7. RESTART APPLICATION (2 min)**
```bash
docker-compose up -d api
docker-compose logs -f api | grep -m 5 "INFO"  # Wait for startup

# Verify health check
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

**8. RUN SMOKE TESTS (3 min)**
```bash
# List personas
curl -s http://localhost:8000/personas?limit=3 | jq '.personas[].name'

# Check a specific persona
curl -s http://localhost:8000/personas/socrates | jq '.name'

# Try to compile a persona (requires API key)
curl -s -X POST http://localhost:8000/v1/compile/socrates \
  -H "X-API-Key: test-key" | jq '.status'
```

**9. RESTORE SERVICE TO NORMAL (5 min)**
- Update status page: "RESOLVED"
- Post in #incident-response: "✅ Database restored. Investigating root cause."
- Monitor error logs for next 30 min
- Schedule post-mortem for next week

**10. DOCUMENT & INVESTIGATE (ongoing)**
```bash
# Save database logs
pg_dump -h localhost -U persona -d persona_hub > /backup/post_recovery_$(date +%s).sql

# Check replication lag (if using replicas)
# Check disk usage
# Check query logs for what happened

# Root cause analysis:
# - Was this a user error (DROP TABLE)?
# - Was this a malicious action (ransomware)?
# - Was this an application bug (data corruption)?
# - Was this infrastructure failure (disk space)?

# Fix the root cause to prevent recurrence
```

---

## Reference

### PostgreSQL Documentation
- https://www.postgresql.org/docs/current/app-pgdump.html
- https://www.postgresql.org/docs/current/backup-file.html

### AWS S3 Documentation
- https://docs.aws.amazon.com/s3/latest/userguide/BucketEncryption.html
- https://docs.aws.amazon.com/cli/latest/userguide/cli-services-s3.html

### Backup Script Reference
- `pg_backup.sh` — Daily full backup to S3
- `pg_restore.sh` — Point-in-time recovery
- `validate_backup.sh` — Backup integrity check
- `failover_test.sh` — Disaster recovery drill

### Environment Variables
```bash
DATABASE_URL              # PostgreSQL connection string
BACKUP_S3_BUCKET         # S3 bucket for backups
AWS_ACCESS_KEY_ID        # AWS credentials
AWS_SECRET_ACCESS_KEY    # AWS credentials
BACKUP_DIR               # Local backup directory
BACKUP_RETENTION_DAYS    # How long to keep backups
```

### Key SLAs
- **RTO:** 2 hours (restore from backup + verify)
- **RPO:** 15 minutes (daily backup at 02:00 UTC = max 24 hours loss)
- **Test Frequency:** Monthly dry-run, quarterly full test
- **Backup Retention:** 30 days
- **Alerting:** Weekly health check, immediate on failure

---

## Checklist

**Weekly:**
- [ ] Backup health check (automated)
- [ ] Verify backup in S3

**Monthly:**
- [ ] Dry-run recovery test (failover_test.sh)
- [ ] Document recovery time
- [ ] Review error logs

**Quarterly:**
- [ ] Full failover test (production-like)
- [ ] Update this runbook if procedures changed
- [ ] Review SLAs (are we meeting RTO/RPO targets?)

**Annually:**
- [ ] Disaster recovery audit
- [ ] Upgrade PostgreSQL version if needed
- [ ] Review S3 bucket policies & encryption
- [ ] Train new team members on recovery procedures

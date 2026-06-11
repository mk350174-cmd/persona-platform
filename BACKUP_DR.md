# Persona Platform — Backup & Disaster Recovery Playbook

**Version:** 1.0  
**Last Updated:** 2026-06-11  
**Owner:** Platform Engineering  
**Review Cycle:** Quarterly  

---

## Table of Contents

1. [Overview & Objectives](#1-overview--objectives)
2. [Backup Strategy](#2-backup-strategy)
3. [RTO / RPO Targets](#3-rto--rpo-targets)
4. [Backup Infrastructure](#4-backup-infrastructure)
5. [Automated Backup Operations](#5-automated-backup-operations)
6. [Manual Backup Procedures](#6-manual-backup-procedures)
7. [Restore Procedures](#7-restore-procedures)
8. [PostgreSQL Streaming Replication Setup](#8-postgresql-streaming-replication-setup)
9. [Point-in-Time Recovery (PITR) with WAL](#9-point-in-time-recovery-pitr-with-wal)
10. [Failover Procedure](#10-failover-procedure)
11. [Disaster Recovery Scenarios](#11-disaster-recovery-scenarios)
12. [DR Drill Procedures](#12-dr-drill-procedures)
13. [Monitoring & Alerting](#13-monitoring--alerting)
14. [Security & Compliance](#14-security--compliance)
15. [Runbook Quick Reference](#15-runbook-quick-reference)
16. [Contact & Escalation](#16-contact--escalation)

---

## 1. Overview & Objectives

This document describes the backup strategy, disaster recovery procedures, and
operational runbooks for the Persona Platform database infrastructure.  It covers
both SQLite (development/single-node) and PostgreSQL (production) deployments.

### 1.1 Scope

- Primary database: PostgreSQL 15+ (production), SQLite (development/staging)
- Alembic-managed schema, SQLAlchemy ORM
- Key data: users, purchases, subscriptions, audit logs, API keys, feature flags
- Related scripts: `scripts/backup.py`, `scripts/restore.py`, `scripts/healthcheck.py`
- CI/CD: `.github/workflows/backup.yml`

### 1.2 Core Principles

- **Data durability first:** Never sacrifice data integrity for convenience.
- **Tested recovery:** Backups not tested regularly are not real backups.
- **Automation:** Every backup and restore operation must be scriptable.
- **Least privilege:** Backup credentials must not have write access to production.
- **Auditability:** Every backup and restore operation must be logged.

---

## 2. Backup Strategy

### 2.1 Backup Types

| Type | Schedule | Retention | Storage |
|---|---|---|---|
| Full logical backup (pg_dump) | Daily at 02:00 UTC | 30 days local, 90 days S3 | Local + S3 |
| WAL archive (continuous) | Continuous | 7 days | S3 |
| Pre-migration snapshot | Before every Alembic migration | 14 days | Local + S3 |
| Weekly full backup | Sunday 02:00 UTC | 1 year | S3 Glacier |
| Monthly full backup | 1st of month 02:00 UTC | 7 years | S3 Glacier Deep Archive |

### 2.2 Backup Contents

Each full backup (`pg_dump --format plain`) includes:

- All schema definitions (tables, indexes, constraints, sequences)
- All table data
- Alembic version table (`alembic_version`)
- Roles and privileges (via `pg_dumpall --globals-only` in a separate step)

### 2.3 Backup Naming Convention

```
# SQLite
{db_name}_backup_{YYYYMMDD}T{HHMMSS}Z.db.gz

# PostgreSQL full dump
{db_name}_backup_{YYYYMMDD}T{HHMMSS}Z.sql.gz

# WAL segment (managed by PostgreSQL)
{timeline}{LSN}.gz
```

### 2.4 Storage Layout (S3)

```
s3://{BACKUP_BUCKET}/
├── daily/
│   ├── persona_backup_20240101T020000Z.sql.gz
│   └── persona_backup_20240102T020000Z.sql.gz
├── weekly/
│   └── persona_backup_20240107T020000Z.sql.gz
├── monthly/
│   └── persona_backup_202401_monthly.sql.gz
├── wal/
│   ├── 000000010000000000000001.gz
│   └── 000000010000000000000002.gz
└── pre-migration/
    └── persona_backup_pre_alembic_007.sql.gz
```

### 2.5 Compression & Encryption

- Compression: gzip level 6 (good balance of speed vs size)
- Encryption at rest: S3 SSE-AES256 (server-side)
- Encryption in transit: TLS 1.2+ enforced on all S3 connections
- Optional: GPG envelope encryption before upload (set `GPG_RECIPIENT` env var)

### 2.6 Backup Verification

After every backup:

1. Gzip integrity test (`gzip -t`)
2. Minimum size check (> 100 KB)
3. SQL syntax sample (first 1000 lines contain `CREATE TABLE` or `INSERT`)
4. Weekly full restore test to isolated environment (see Section 12)

---

## 3. RTO / RPO Targets

### 3.1 Definitions

- **RTO (Recovery Time Objective):** Maximum acceptable downtime during a
  disaster — from incident declaration to service restoration.
- **RPO (Recovery Point Objective):** Maximum acceptable data loss — the age
  of the last recoverable backup at the time of failure.

### 3.2 Targets by Tier

| Incident Tier | Description | RTO | RPO |
|---|---|---|---|
| Tier 1 — Full outage | DB completely inaccessible | **< 1 hour** | **< 24 hours** |
| Tier 2 — Data corruption | Partial table corruption | **< 2 hours** | **< 1 hour** (WAL PITR) |
| Tier 3 — Replica failure | Primary OK, replica down | **< 30 minutes** | 0 (no data loss) |
| Tier 4 — Storage failure | Disk failure on primary | **< 1 hour** | **< 15 minutes** (WAL) |

### 3.3 How to Achieve These Targets

| Target | Mechanism |
|---|---|
| RPO < 24 hours | Daily full backups at 02:00 UTC |
| RPO < 1 hour | WAL archiving (continuous) to S3 |
| RPO near zero | Synchronous streaming replication (optional) |
| RTO < 1 hour | Documented runbook + automated failover scripts |
| RTO < 30 minutes | Hot standby replica (streaming replication) |

---

## 4. Backup Infrastructure

### 4.1 Required Tools

```bash
# Install on backup runner / application server
sudo apt-get install -y postgresql-client gzip awscli

# Python dependencies
pip install boto3 botocore sqlalchemy psycopg2-binary
```

### 4.2 Required Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:password@host:5432/persona

# S3 backup storage (optional but strongly recommended for production)
S3_BACKUP_BUCKET=persona-platform-backups
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# Retention policy
BACKUP_RETENTION_DAYS=30

# Local backup directory
BACKUP_DIR=/var/backups/persona

# Log file (optional)
LOG_FILE=/var/log/persona/backup.log
```

### 4.3 IAM Policy for Backup User (S3)

The backup runner needs the following minimum IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::persona-platform-backups",
        "arn:aws:s3:::persona-platform-backups/*"
      ]
    }
  ]
}
```

The backup user must NOT have:
- Write access to production S3 application buckets
- IAM management permissions
- EC2/RDS instance modification permissions

### 4.4 S3 Bucket Configuration

```bash
# Create bucket with versioning and lifecycle rules
aws s3api create-bucket \
  --bucket persona-platform-backups \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket persona-platform-backups \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket persona-platform-backups \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket persona-platform-backups \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'
```

**Lifecycle Policy** — apply via AWS console or CLI:

```json
{
  "Rules": [
    {
      "ID": "daily-to-glacier",
      "Filter": {"Prefix": "daily/"},
      "Status": "Enabled",
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 365}
    },
    {
      "ID": "monthly-deep-archive",
      "Filter": {"Prefix": "monthly/"},
      "Status": "Enabled",
      "Transitions": [
        {"Days": 60, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 2555}
    },
    {
      "ID": "wal-retention",
      "Filter": {"Prefix": "wal/"},
      "Status": "Enabled",
      "Expiration": {"Days": 7}
    }
  ]
}
```

---

## 5. Automated Backup Operations

### 5.1 GitHub Actions Workflow

File: `.github/workflows/backup.yml`

The workflow runs daily at 02:00 UTC and:

1. Checks out the repository
2. Installs Python and dependencies
3. Runs `scripts/backup.py` with production `DATABASE_URL` secret
4. Uploads the backup as a GitHub Actions artifact (7-day retention)
5. Runs a post-backup health check against the database
6. Creates a GitHub Issue on failure for tracking

**Required Secrets:**

| Secret | Description |
|---|---|
| `DATABASE_URL` | Full PostgreSQL connection string |
| `S3_BACKUP_BUCKET` | S3 bucket name (optional) |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 upload |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 upload |
| `AWS_DEFAULT_REGION` | AWS region (default: us-east-1) |

**Manual Trigger:**

```bash
# Via GitHub CLI
gh workflow run backup.yml

# With custom parameters
gh workflow run backup.yml \
  -f keep_days=60 \
  -f dry_run=false
```

### 5.2 Cron-based Backup (Alternative to GitHub Actions)

For self-hosted deployments, add to crontab:

```crontab
# Daily backup at 02:00 UTC
0 2 * * * /usr/bin/python3 /opt/persona/scripts/backup.py \
  --output /var/backups/persona \
  --db-url "$DATABASE_URL" \
  --keep-days 30 \
  --log-file /var/log/persona/backup.log

# Weekly full backup (Sundays at 02:30 UTC) — kept for 1 year
30 2 * * 0 /usr/bin/python3 /opt/persona/scripts/backup.py \
  --output /var/backups/persona/weekly \
  --db-url "$DATABASE_URL" \
  --keep-days 365
```

### 5.3 Pre-Migration Backup

Run this before every Alembic migration:

```bash
#!/bin/bash
# scripts/pre-migration-backup.sh
set -euo pipefail

MIGRATION_ID="${1:-unknown}"
OUTPUT_DIR="${BACKUP_DIR:-/var/backups/persona}/pre-migration"
DB_URL="${DATABASE_URL:-sqlite:///./persona_store.db}"

echo "Running pre-migration backup for migration: $MIGRATION_ID"

python scripts/backup.py \
  --output "$OUTPUT_DIR" \
  --db-url "$DB_URL" \
  --keep-days 14 \
  --verbose

echo "Pre-migration backup complete."
```

Add to Alembic `env.py`:

```python
# In alembic/env.py — before run_migrations_online()
import subprocess
import os

def run_migrations_online():
    # Take a pre-migration backup
    if os.getenv("PRE_MIGRATION_BACKUP", "1") == "1":
        subprocess.run([
            "python", "scripts/backup.py",
            "--output", os.getenv("BACKUP_DIR", "/tmp/persona_backups/pre-migration"),
            "--db-url", os.getenv("DATABASE_URL", "sqlite:///./persona_store.db"),
            "--keep-days", "14",
        ], check=False)  # Non-fatal: don't block migration on backup failure
```

---

## 6. Manual Backup Procedures

### 6.1 SQLite Backup (Development / Staging)

```bash
# Basic backup
python scripts/backup.py \
  --output /tmp/backups \
  --db-url sqlite:///./persona_store.db

# With verbose output
python scripts/backup.py \
  --output /tmp/backups \
  --db-url sqlite:///./persona_store.db \
  --verbose

# List existing backups
python scripts/backup.py --list --output /tmp/backups

# Clean up old backups
python scripts/backup.py --cleanup --output /tmp/backups --keep-days 7
```

### 6.2 PostgreSQL Backup (Production)

```bash
# Standard backup
python scripts/backup.py \
  --output /var/backups/persona \
  --db-url "$DATABASE_URL" \
  --s3-bucket persona-platform-backups

# Direct pg_dump (without script)
PGPASSWORD="$DB_PASSWORD" pg_dump \
  --host "$DB_HOST" \
  --port 5432 \
  --username "$DB_USER" \
  --dbname persona \
  --format plain \
  --no-password \
  | gzip -6 > "/var/backups/persona/persona_backup_$(date -u '+%Y%m%dT%H%M%SZ').sql.gz"

# Custom format backup (faster restores, supports parallel restore)
pg_dump \
  --host "$DB_HOST" \
  --port 5432 \
  --username "$DB_USER" \
  --dbname persona \
  --format custom \
  --compress 6 \
  --file "/var/backups/persona/persona_backup_$(date -u '+%Y%m%dT%H%M%SZ').dump"
```

### 6.3 Backup Global Objects (Roles, Tablespaces)

```bash
# Dump global objects separately (run as superuser)
PGPASSWORD="$DB_SUPERUSER_PASSWORD" pg_dumpall \
  --host "$DB_HOST" \
  --port 5432 \
  --username postgres \
  --globals-only \
  | gzip -6 > "/var/backups/persona/globals_$(date -u '+%Y%m%dT%H%M%SZ').sql.gz"
```

### 6.4 Verify a Backup

```bash
# Check gzip integrity
gzip -t /var/backups/persona/persona_backup_20240101T020000Z.sql.gz
echo "Exit code: $?"  # 0 = valid

# Using the restore script validator
python scripts/restore.py \
  --validate \
  --backup /var/backups/persona/persona_backup_20240101T020000Z.sql.gz

# Quick SQL syntax check
gunzip -c /var/backups/persona/persona_backup_20240101T020000Z.sql.gz | head -100
```

---

## 7. Restore Procedures

### 7.1 SQLite Restore

```bash
# Restore to original location (creates safety copy of existing DB)
python scripts/restore.py \
  --backup /tmp/backups/persona_store_backup_20240101T020000Z.db.gz \
  --db-url sqlite:///./persona_store.db

# Restore to a different path for inspection
python scripts/restore.py \
  --backup /tmp/backups/persona_store_backup_20240101T020000Z.db.gz \
  --db-url sqlite:////tmp/persona_inspect.db

# Dry run (validate without writing)
python scripts/restore.py \
  --backup /tmp/backups/persona_store_backup_20240101T020000Z.db.gz \
  --db-url sqlite:///./persona_store.db \
  --dry-run
```

### 7.2 PostgreSQL Restore — Full Database

**Step 1: Stop application traffic**

```bash
# On load balancer / reverse proxy — disable routing to the application
# Or set maintenance mode flag in application config
```

**Step 2: Create a clean target database**

```bash
# Connect as superuser and drop/recreate the database
PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
  --host "$DB_HOST" \
  --port 5432 \
  --username postgres \
  --command "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'persona' AND pid <> pg_backend_pid();"

PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
  --host "$DB_HOST" \
  --port 5432 \
  --username postgres \
  --command "DROP DATABASE IF EXISTS persona;"

PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
  --host "$DB_HOST" \
  --port 5432 \
  --username postgres \
  --command "CREATE DATABASE persona OWNER persona_user;"
```

**Step 3: Restore using the script**

```bash
python scripts/restore.py \
  --backup /var/backups/persona/persona_backup_20240101T020000Z.sql.gz \
  --db-url "postgresql://persona_user:$DB_PASSWORD@$DB_HOST/persona" \
  --verbose
```

**Step 4: Restore global objects (if needed)**

```bash
gunzip -c /var/backups/persona/globals_20240101T020000Z.sql.gz \
  | PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
    --host "$DB_HOST" \
    --port 5432 \
    --username postgres
```

**Step 5: Run post-restore health check**

```bash
python scripts/healthcheck.py \
  --db-url "postgresql://persona_user:$DB_PASSWORD@$DB_HOST/persona" \
  --verbose
```

**Step 6: Re-enable application traffic**

```bash
# Re-enable load balancer routing or clear maintenance mode flag
```

### 7.3 PostgreSQL Restore — Custom Format (Parallel)

```bash
# Restore with pg_restore (faster than psql for large databases)
# First, decompress if needed
gunzip persona_backup_20240101T020000Z.dump.gz

pg_restore \
  --host "$DB_HOST" \
  --port 5432 \
  --username persona_user \
  --dbname persona \
  --no-password \
  --jobs 4 \
  --clean \
  --if-exists \
  --verbose \
  persona_backup_20240101T020000Z.dump
```

### 7.4 Restore from S3

```bash
# Download and restore in one command
python scripts/restore.py \
  --s3-bucket persona-platform-backups \
  --s3-key daily/persona_backup_20240101T020000Z.sql.gz \
  --db-url "postgresql://persona_user:$DB_PASSWORD@$DB_HOST/persona"

# List available backups in S3 first
python scripts/restore.py \
  --list-s3 \
  --s3-bucket persona-platform-backups \
  --s3-prefix daily/
```

### 7.5 Restore a Single Table

```bash
# Extract a specific table from a full backup
gunzip -c /var/backups/persona/persona_backup_20240101T020000Z.sql.gz \
  | grep -A 99999 "^COPY public.users " \
  | head -n "$(grep -c '' <<< "$(gunzip -c /var/backups/persona/persona_backup_20240101T020000Z.sql.gz | grep -A 99999 "^COPY public.users " | sed -n '1,/^\\\./p')")" \
  | PGPASSWORD="$DB_PASSWORD" psql --host "$DB_HOST" --username persona_user persona

# Preferred: use pg_restore with a custom-format backup
pg_restore \
  --host "$DB_HOST" \
  --username persona_user \
  --dbname persona \
  --table users \
  --data-only \
  persona_backup_20240101T020000Z.dump
```

---

## 8. PostgreSQL Streaming Replication Setup

Streaming replication provides a hot standby that can take over with minimal
downtime and no data loss (when configured as synchronous).

### 8.1 Architecture

```
┌─────────────────┐     WAL stream      ┌─────────────────┐
│  Primary (RW)   │ ──────────────────► │  Standby (RO)   │
│  192.168.1.10   │                     │  192.168.1.11   │
└─────────────────┘                     └─────────────────┘
        │                                       │
        └──────── S3 WAL Archive ───────────────┘
```

### 8.2 Primary Server Configuration

Edit `postgresql.conf` on the primary:

```conf
# Replication settings
wal_level = replica                    # Minimum for streaming replication
max_wal_senders = 5                    # Number of replication connections allowed
wal_keep_size = 1024                   # MB of WAL to retain for lagging standbys
max_replication_slots = 5             # Replication slots for reliable lag tracking

# WAL archiving (feeds into PITR)
archive_mode = on
archive_command = 'aws s3 cp %p s3://$S3_BACKUP_BUCKET/wal/%f'
archive_timeout = 300                  # Force archive every 5 minutes even if no WAL

# Performance tuning for replication
synchronous_commit = on                # Set to 'remote_apply' for zero-RPO
wal_compression = on

# Monitoring
track_commit_timestamp = on
```

Edit `pg_hba.conf` on the primary to allow the standby to connect:

```conf
# Replication connections
host  replication  replicator  192.168.1.11/32  scram-sha-256
```

Create the replication user:

```sql
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'strong_password_here';
```

Reload PostgreSQL:

```bash
sudo systemctl reload postgresql
```

### 8.3 Standby Server Setup

**Step 1: Take a base backup from the primary**

```bash
# On the standby server
PGPASSWORD="replicator_password" pg_basebackup \
  --host 192.168.1.10 \
  --port 5432 \
  --username replicator \
  --pgdata /var/lib/postgresql/15/main \
  --wal-method stream \
  --checkpoint fast \
  --progress \
  --verbose
```

**Step 2: Create standby.signal**

```bash
# This file's presence triggers standby mode
touch /var/lib/postgresql/15/main/standby.signal
```

**Step 3: Configure recovery on the standby**

Add to `postgresql.conf` (or create `postgresql.auto.conf`):

```conf
# Connection to primary
primary_conninfo = 'host=192.168.1.10 port=5432 user=replicator password=replicator_password application_name=standby1'

# WAL restore from S3 archive (fallback if streaming falls behind)
restore_command = 'aws s3 cp s3://$S3_BACKUP_BUCKET/wal/%f %p'

# Allow read-only queries on standby
hot_standby = on
hot_standby_feedback = on            # Prevents hot_standby_feedback conflicts
```

**Step 4: Start the standby**

```bash
sudo systemctl start postgresql
```

**Step 5: Verify replication**

```sql
-- On primary: check replication status
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- On standby: confirm recovery mode
SELECT pg_is_in_recovery();  -- should return true

-- Check replication lag
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

### 8.4 Synchronous Replication (Zero RPO)

To prevent data loss even on primary crash, configure synchronous replication:

```conf
# On primary, in postgresql.conf
synchronous_standby_names = 'standby1'   # Must match application_name on standby
synchronous_commit = remote_apply        # Wait for standby to apply (safest, slowest)
# Alternative: remote_write (faster, small window of data loss)
```

**Trade-off:** With `synchronous_commit = remote_apply`, every write waits for
the standby to confirm.  This adds latency equal to the network round-trip to the
standby.  For Persona Platform, `synchronous_commit = on` (default) is acceptable
since the WAL archive provides the RPO guarantee.

### 8.5 Replication Monitoring

```bash
# Check replication lag continuously
watch -n 5 'psql "$DATABASE_URL" -c "
SELECT
  application_name,
  state,
  pg_size_pretty(sent_lsn - replay_lsn) AS lag_size,
  now() - reply_time AS last_reply
FROM pg_stat_replication;"'
```

Add a health check alert (see Section 13):

```python
# Trigger alert if replication lag > 100 MB
python scripts/healthcheck.py --db-url "$DATABASE_URL" --json \
  | jq '.checks.replication.max_lag_bytes > 104857600'
```

---

## 9. Point-in-Time Recovery (PITR) with WAL

PITR allows recovery to any point between backups, limited only by WAL archive
completeness.  This is the primary mechanism for recovering from data corruption
or accidental DELETE/TRUNCATE.

### 9.1 Prerequisites

- WAL archiving enabled (`archive_mode = on` with `archive_command` to S3)
- At least one full base backup taken after `archive_mode` was enabled

### 9.2 PITR Procedure

**Scenario:** A developer accidentally ran `DELETE FROM users WHERE 1=1` at
2024-01-15 14:30:00 UTC.  We need to recover to 14:29:00 UTC.

**Step 1: Identify the last full backup before the incident**

```bash
# List available backups
python scripts/restore.py \
  --list-s3 \
  --s3-bucket persona-platform-backups \
  --s3-prefix daily/

# Identify the last backup before 14:30 UTC on 2024-01-15
# e.g.: daily/persona_backup_20240115T020000Z.sql.gz
```

**Step 2: Stop the primary**

```bash
sudo systemctl stop postgresql
```

**Step 3: Restore the base backup to a new data directory**

```bash
# Create a recovery directory
RECOVERY_DIR=/var/lib/postgresql/15/recovery
sudo mkdir -p "$RECOVERY_DIR"
sudo chown postgres:postgres "$RECOVERY_DIR"

# Download and restore the base backup
python scripts/restore.py \
  --s3-bucket persona-platform-backups \
  --s3-key daily/persona_backup_20240115T020000Z.sql.gz \
  --db-url "postgresql://persona_user:$DB_PASSWORD@localhost/persona"
```

**Step 4: Configure PITR recovery target**

Create `/etc/postgresql/15/main/recovery.conf` (Postgres 11 and earlier) or
add to `postgresql.auto.conf` (Postgres 12+):

```conf
# PITR target time (one minute before the accident)
recovery_target_time = '2024-01-15 14:29:00 UTC'
recovery_target_action = 'promote'        # Promote to primary after reaching target

# WAL restore command
restore_command = 'aws s3 cp s3://persona-platform-backups/wal/%f %p'

# Standby signal is NOT required for PITR — this is a recovery, not a replica
```

Create the recovery signal file:

```bash
touch /var/lib/postgresql/15/main/recovery.signal
```

**Step 5: Start PostgreSQL and monitor recovery**

```bash
sudo systemctl start postgresql

# Tail the PostgreSQL log to watch recovery progress
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

Expected log output:

```
LOG:  starting point-in-time recovery to 2024-01-15 14:29:00+00
LOG:  restored log file "000000010000000000000001" from archive
...
LOG:  recovery stopping before commit of transaction 1234, time 2024-01-15 14:29:01+00
LOG:  pausing at the end of recovery
HINT:  Execute pg_wal_replay_resume() to promote.
```

**Step 6: Verify data and promote**

```bash
# Connect to the recovering instance (read-only at this point)
PGPASSWORD="$DB_PASSWORD" psql \
  --host localhost \
  --username persona_user \
  persona \
  --command "SELECT COUNT(*) FROM users;"  # Verify users are present

# Promote the instance to primary
PGPASSWORD="$DB_PASSWORD" psql \
  --host localhost \
  --username postgres \
  --command "SELECT pg_wal_replay_resume();"
```

**Step 7: Update application connection strings and restore traffic**

```bash
# Point DATABASE_URL to the recovered instance
export DATABASE_URL="postgresql://persona_user:$DB_PASSWORD@localhost/persona"

# Run health check
python scripts/healthcheck.py --db-url "$DATABASE_URL"
```

### 9.3 PITR Time Granularity

WAL archiving with `archive_timeout = 300` guarantees that the worst-case data
loss is 5 minutes (time of the last forced WAL switch).  In practice, on a busy
production system, WAL segments are archived every few seconds.

---

## 10. Failover Procedure

### 10.1 When to Invoke Failover

Invoke the failover procedure when:

- The primary PostgreSQL instance is completely unresponsive for > 5 minutes
- The primary host has suffered a hardware failure
- The primary is returning corrupt data
- A storage device on the primary has failed

**Do NOT invoke failover for:**

- Temporary network partitions (wait up to 10 minutes)
- High replication lag alone (investigate cause first)
- Planned maintenance (use scheduled switchover instead)

### 10.2 Automatic Failover (with Patroni / pg_auto_failover)

For production deployments, use an orchestrator.  Example with Patroni:

```bash
# Check cluster status
patronictl -c /etc/patroni/patroni.yml list

# Initiate failover
patronictl -c /etc/patroni/patroni.yml failover persona --master primary-node --candidate standby-node

# Monitor failover progress
patronictl -c /etc/patroni/patroni.yml history persona
```

### 10.3 Manual Failover Procedure

**Step 1: Confirm primary is truly down**

```bash
# Attempt to connect from multiple locations
PGPASSWORD="$DB_PASSWORD" pg_isready --host "$PRIMARY_HOST" --port 5432
# Should return: "192.168.1.10:5432 - no response"
```

**Step 2: Check standby replication lag (before promoting)**

```bash
PGPASSWORD="$DB_PASSWORD" psql \
  --host "$STANDBY_HOST" \
  --username persona_user \
  persona \
  --command "SELECT now() - pg_last_xact_replay_timestamp() AS lag;"
```

Log the current LSN for incident reporting:

```bash
PGPASSWORD="$DB_PASSWORD" psql \
  --host "$STANDBY_HOST" \
  --username persona_user \
  persona \
  --command "SELECT pg_last_wal_replay_lsn();"
```

**Step 3: Promote the standby**

```bash
# Method 1: pg_ctl promote
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/15/main

# Method 2: SQL command (Postgres 12+)
PGPASSWORD="$DB_PASSWORD" psql \
  --host "$STANDBY_HOST" \
  --username postgres \
  --command "SELECT pg_promote();"
```

**Step 4: Verify promotion**

```bash
PGPASSWORD="$DB_PASSWORD" psql \
  --host "$STANDBY_HOST" \
  --username persona_user \
  persona \
  --command "SELECT pg_is_in_recovery();"
# Should return: false (meaning it is now the primary)
```

**Step 5: Update application configuration**

```bash
# Update DATABASE_URL in application config / environment
# For Kubernetes: patch the secret
kubectl patch secret persona-db-secret \
  --patch '{"stringData": {"DATABASE_URL": "postgresql://persona_user:'"$DB_PASSWORD"'@'"$STANDBY_HOST"'/persona"}}'

# Restart application pods to pick up new connection string
kubectl rollout restart deployment/persona-api
```

**Step 6: Run health check on new primary**

```bash
python scripts/healthcheck.py \
  --db-url "postgresql://persona_user:$DB_PASSWORD@$STANDBY_HOST/persona" \
  --verbose
```

**Step 7: Update monitoring and alerting targets**

Update your monitoring system (Grafana, Datadog, etc.) to point to the new primary.

**Step 8: Document the incident**

Create a post-mortem document including:
- Time of failure detection
- LSN at time of failover
- Estimated data loss (if any)
- Time to recovery (measure against RTO target)
- Root cause analysis

### 10.4 Post-Failover: Rebuilding the Former Primary as Standby

Once the original primary is recovered:

```bash
# On the former primary, stop PostgreSQL if it restarted
sudo systemctl stop postgresql

# Re-synchronize from the new primary using pg_basebackup
PGPASSWORD="replicator_password" pg_basebackup \
  --host "$STANDBY_HOST" \
  --port 5432 \
  --username replicator \
  --pgdata /var/lib/postgresql/15/main \
  --wal-method stream \
  --checkpoint fast \
  --progress

# Create standby.signal
touch /var/lib/postgresql/15/main/standby.signal

# Update primary_conninfo to point to the new primary
sed -i "s/primary_conninfo = .*/primary_conninfo = 'host=$STANDBY_HOST port=5432 user=replicator password=replicator_password'/" \
  /var/lib/postgresql/15/main/postgresql.auto.conf

# Start as standby
sudo systemctl start postgresql
```

---

## 11. Disaster Recovery Scenarios

### 11.1 Scenario: Accidental Table DROP or TRUNCATE

**Severity:** High  
**Target RTO:** < 2 hours  
**Target RPO:** < 1 hour (WAL PITR)

```bash
# 1. Note the exact time of the accident (check audit logs / application logs)
grep "TRUNCATE\|DROP TABLE" /var/log/postgresql/postgresql-15-main.log | tail -20

# 2. Identify last good WAL segment before accident
# 3. Follow PITR procedure in Section 9.2 with recovery_target_time = (accident_time - 1 minute)
# 4. Export affected tables to CSV from recovered instance
psql "$RECOVERY_DB_URL" --command "\COPY users TO '/tmp/users_recovered.csv' CSV HEADER"

# 5. Import into production database
psql "$DATABASE_URL" --command "\COPY users FROM '/tmp/users_recovered.csv' CSV HEADER"

# 6. Run health check and verify row counts
python scripts/healthcheck.py --db-url "$DATABASE_URL"
```

### 11.2 Scenario: Full Database Host Failure

**Severity:** Critical  
**Target RTO:** < 1 hour  
**Target RPO:** < 24 hours (last daily backup)

```bash
# 1. Verify host is unresponsive (not just network hiccup)
ping -c 10 "$DB_HOST"
PGPASSWORD="$DB_PASSWORD" pg_isready --host "$DB_HOST" --port 5432

# 2. If streaming replica exists, invoke failover (Section 10.3)

# 3. If no replica: provision new database server
#    - Spin up new EC2 / VM
#    - Install PostgreSQL 15
#    - Restore from S3 backup (Section 7.4)

# 4. Restore latest backup
python scripts/restore.py \
  --s3-bucket persona-platform-backups \
  --s3-key "daily/$(aws s3 ls s3://persona-platform-backups/daily/ | sort | tail -1 | awk '{print $4}')" \
  --db-url "postgresql://persona_user:$DB_PASSWORD@$NEW_DB_HOST/persona" \
  --create-db

# 5. Apply WAL archives from last backup to present (if available)
# 6. Update application DATABASE_URL
# 7. Health check and restore traffic
python scripts/healthcheck.py --db-url "postgresql://persona_user:$DB_PASSWORD@$NEW_DB_HOST/persona"
```

### 11.3 Scenario: Backup File Corruption

**Severity:** Medium  
**Recovery:** Use the next most recent backup

```bash
# Verify all recent backups for integrity
for f in /var/backups/persona/*.gz; do
  if gzip -t "$f" 2>/dev/null; then
    echo "OK: $f"
  else
    echo "CORRUPTED: $f"
  fi
done

# Or use the script
python scripts/restore.py --validate --backup /var/backups/persona/backup.sql.gz
```

### 11.4 Scenario: S3 Bucket Deletion or Access Loss

**Severity:** High  
**Recovery:** Use local backup copies + GitHub Actions artifact

```bash
# Check GitHub Actions artifacts (kept 7 days)
gh run list --workflow backup.yml --limit 10

# Download latest artifact
RUN_ID=$(gh run list --workflow backup.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run download "$RUN_ID" --name "persona-db-backup-$RUN_ID" --dir /tmp/restored_backups

# Restore from artifact
python scripts/restore.py \
  --backup /tmp/restored_backups/*.sql.gz \
  --db-url "$DATABASE_URL"
```

### 11.5 Scenario: Schema Migration Failure

**Severity:** Medium  
**Recovery:** Roll back to pre-migration snapshot

```bash
# List pre-migration backups
python scripts/backup.py --list --output "${BACKUP_DIR}/pre-migration"

# Restore pre-migration backup
python scripts/restore.py \
  --backup "${BACKUP_DIR}/pre-migration/persona_backup_pre_alembic_007.sql.gz" \
  --db-url "$DATABASE_URL"

# Verify schema version
python scripts/healthcheck.py --db-url "$DATABASE_URL" | grep "schema_version"

# Fix the migration and re-run
alembic upgrade head
```

---

## 12. DR Drill Procedures

### 12.1 Drill Schedule

| Drill Type | Frequency | Duration | Owner |
|---|---|---|---|
| Backup validation | Weekly (automated) | 30 min | Platform Engineering |
| Full restore test | Monthly | 2 hours | Platform Engineering |
| Failover drill | Quarterly | 4 hours | Platform Engineering + DevOps |
| PITR drill | Semi-annual | 4 hours | Platform Engineering |
| Full DR drill | Annual | 1 day | All Engineering |

### 12.2 Monthly Full Restore Drill

**Objective:** Verify that the latest backup can be fully restored to a fresh
database within the RTO target.

**Procedure:**

```bash
#!/bin/bash
# scripts/dr-drill-monthly.sh
set -euo pipefail

DRILL_DATE=$(date -u '+%Y%m%d')
DRILL_DB="persona_dr_drill_${DRILL_DATE}"
DRILL_LOG="/tmp/dr_drill_${DRILL_DATE}.log"
BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"

echo "=== DR Drill — Full Restore Test — $DRILL_DATE ===" | tee "$DRILL_LOG"

# Step 1: Identify latest backup
echo "[1/6] Identifying latest backup..." | tee -a "$DRILL_LOG"
if [ -n "$BACKUP_BUCKET" ]; then
  LATEST_KEY=$(aws s3 ls "s3://$BACKUP_BUCKET/daily/" \
    | sort | tail -1 | awk '{print "daily/" $4}')
  echo "Latest S3 backup: $LATEST_KEY" | tee -a "$DRILL_LOG"
else
  LATEST_BACKUP=$(ls -t "${BACKUP_DIR:-/tmp/persona_backups}"/*.sql.gz 2>/dev/null | head -1)
  echo "Latest local backup: $LATEST_BACKUP" | tee -a "$DRILL_LOG"
fi

# Step 2: Start timer
START_TIME=$(date +%s)

# Step 3: Create isolated drill database
echo "[2/6] Creating drill database: $DRILL_DB..." | tee -a "$DRILL_LOG"
PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
  --host "$DB_HOST" \
  --username postgres \
  --command "CREATE DATABASE $DRILL_DB;" 2>&1 | tee -a "$DRILL_LOG"

DRILL_URL="postgresql://persona_user:$DB_PASSWORD@$DB_HOST/$DRILL_DB"

# Step 4: Restore backup
echo "[3/6] Restoring backup..." | tee -a "$DRILL_LOG"
if [ -n "$BACKUP_BUCKET" ]; then
  python scripts/restore.py \
    --s3-bucket "$BACKUP_BUCKET" \
    --s3-key "$LATEST_KEY" \
    --db-url "$DRILL_URL" \
    --verbose 2>&1 | tee -a "$DRILL_LOG"
else
  python scripts/restore.py \
    --backup "$LATEST_BACKUP" \
    --db-url "$DRILL_URL" \
    --verbose 2>&1 | tee -a "$DRILL_LOG"
fi

# Step 5: Health check
echo "[4/6] Running health check on restored DB..." | tee -a "$DRILL_LOG"
python scripts/healthcheck.py \
  --db-url "$DRILL_URL" \
  --verbose 2>&1 | tee -a "$DRILL_LOG"

# Step 6: Record time
END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
echo "[5/6] Restore completed in ${ELAPSED} seconds." | tee -a "$DRILL_LOG"

# Verify against RTO target (3600 seconds = 1 hour)
if [ "$ELAPSED" -gt 3600 ]; then
  echo "WARNING: Restore exceeded RTO target of 1 hour!" | tee -a "$DRILL_LOG"
fi

# Step 7: Cleanup
echo "[6/6] Cleaning up drill database..." | tee -a "$DRILL_LOG"
PGPASSWORD="$DB_SUPERUSER_PASSWORD" psql \
  --host "$DB_HOST" \
  --username postgres \
  --command "DROP DATABASE $DRILL_DB;" 2>&1 | tee -a "$DRILL_LOG"

echo "=== DR Drill Complete ===" | tee -a "$DRILL_LOG"
echo "Log: $DRILL_LOG"
```

### 12.3 Quarterly Failover Drill

**Objective:** Test the full failover procedure in a staging environment.

**Checklist:**

- [ ] Notify all team members 1 day in advance
- [ ] Confirm staging replica is in sync with staging primary
- [ ] Confirm application team has staging environment ready for testing
- [ ] Execute failover (Section 10.3) against staging
- [ ] Measure time from failover start to application reconnection
- [ ] Run full suite of application smoke tests on new primary
- [ ] Document actual RTO achieved vs target
- [ ] Rebuild former staging primary as new standby
- [ ] Write drill report

### 12.4 Drill Report Template

```markdown
# DR Drill Report — {date}

## Drill Type
[ ] Full Restore  [ ] Failover  [ ] PITR  [ ] Full DR

## Environment
- Primary host: 
- Standby host: 
- Backup used: 
- Database size: 

## Results
| Metric | Target | Actual | Pass/Fail |
|---|---|---|---|
| RTO | < 1 hour | | |
| RPO | < 24 hours | | |
| Restore time | | | |
| Health check | HEALTHY | | |

## Issues Encountered

## Action Items

## Sign-off
- Conducted by: 
- Reviewed by: 
```

---

## 13. Monitoring & Alerting

### 13.1 Health Check Metrics

Run `scripts/healthcheck.py` on a schedule and export metrics:

```bash
# Cron: every 5 minutes
*/5 * * * * python /opt/persona/scripts/healthcheck.py \
  --db-url "$DATABASE_URL" \
  --json > /var/log/persona/healthcheck_latest.json

# Parse and alert on non-healthy status
RESULT=$(python scripts/healthcheck.py --db-url "$DATABASE_URL" --json)
STATUS=$(echo "$RESULT" | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
  # Send alert via PagerDuty / OpsGenie / Slack webhook
  curl -X POST "$SLACK_WEBHOOK_URL" \
    --header 'Content-Type: application/json' \
    --data "{\"text\": \"DB Health Alert: $STATUS — $(echo $RESULT | jq -r '.summary')\"}"
fi
```

### 13.2 Backup Freshness Check

```bash
#!/bin/bash
# Alert if no backup was produced in the last 25 hours
LATEST_BACKUP_AGE_H=$(python scripts/backup.py --list --output "$BACKUP_DIR" \
  | awk 'NR>3 {print $3; exit}')

if [ -z "$LATEST_BACKUP_AGE_H" ] || (( $(echo "$LATEST_BACKUP_AGE_H > 25" | bc -l) )); then
  echo "ALERT: No recent backup found or backup is too old (${LATEST_BACKUP_AGE_H}h)"
  # Send alert
fi
```

### 13.3 Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold | Check Script |
|---|---|---|---|
| Backup age | > 25 hours | > 48 hours | `backup.py --list` |
| DB connection latency | > 500 ms | > 2000 ms | `healthcheck.py` |
| Replication lag | > 10 MB | > 100 MB | `healthcheck.py` |
| Backup size delta | +50% from baseline | +200% or -50% | `backup.py --list` |
| S3 backup count | < 5 | < 2 | `restore.py --list-s3` |
| WAL archive lag | > 10 min | > 30 min | PostgreSQL logs |

### 13.4 CloudWatch / Prometheus Integration

Export health check results to your monitoring system:

```python
# Example: push metrics to CloudWatch
import boto3
import json
import subprocess

result = json.loads(subprocess.check_output([
    "python", "scripts/healthcheck.py",
    "--db-url", os.environ["DATABASE_URL"],
    "--json",
]))

cw = boto3.client("cloudwatch")
cw.put_metric_data(
    Namespace="PersonaPlatform/Database",
    MetricData=[
        {
            "MetricName": "ConnectionLatencyMs",
            "Value": result["checks"]["connection"]["latency_ms"],
            "Unit": "Milliseconds",
        },
        {
            "MetricName": "DBStatus",
            "Value": 0 if result["status"] == "healthy" else 1,
            "Unit": "None",
        },
    ],
)
```

### 13.5 Alerting Runbook

When a monitoring alert fires:

| Alert | Immediate Action | Escalation |
|---|---|---|
| Backup failed | Check GitHub Actions logs; run backup manually | If persists > 1 hour: page on-call |
| DB down | Run healthcheck.py; check Postgres logs | Immediately page on-call |
| DB degraded | Run healthcheck.py; identify cause | If persists > 30 min: page on-call |
| Replication lag > 100 MB | Check primary/standby connectivity | If lag grows: prepare failover |
| No backup in 48h | Run manual backup; check cron/workflow | Page on-call immediately |

---

## 14. Security & Compliance

### 14.1 Credential Rotation Schedule

| Credential | Rotation Frequency | Method |
|---|---|---|
| `DATABASE_URL` password | 90 days | Alembic + application restart |
| AWS backup IAM keys | 90 days | AWS IAM key rotation |
| Replication user password | 180 days | `ALTER ROLE replicator PASSWORD '...'` |

### 14.2 Access Control

- Backup files in S3 must never be publicly accessible
- Backup decryption keys must be stored separately from encrypted backups
- Only the backup IAM role may write to `s3://persona-platform-backups/`
- Application IAM roles must NOT have read access to backup bucket

### 14.3 Audit Trail

Every backup and restore operation is logged with:

- Timestamp (UTC)
- Operator (GitHub Actions run ID or username)
- Database URL (password redacted)
- Backup file path/S3 key
- Duration
- Exit code

Logs are retained for 1 year minimum in `/var/log/persona/backup.log` and/or
the GitHub Actions workflow log.

### 14.4 Data Classification

Backup files contain PII (email addresses, payment tokens) and must be treated
as confidential:

- S3 SSE-AES256 encryption enabled
- S3 bucket versioning enabled
- S3 bucket public access blocked
- Backup files must be deleted securely (S3 lifecycle policy)
- Never store backup files on developer laptops unencrypted

### 14.5 Compliance Checklist

```
[ ] S3 bucket has public access blocked
[ ] S3 bucket has SSE-AES256 encryption enabled
[ ] S3 bucket has versioning enabled
[ ] Lifecycle rules configured for retention tiers
[ ] Backup IAM user has least-privilege permissions
[ ] Backup log retention >= 1 year
[ ] DR drill completed within the last quarter
[ ] Backup freshness monitoring alerts configured
[ ] Credentials rotated within the last 90 days
```

---

## 15. Runbook Quick Reference

### 15.1 One-Liners

```bash
# Quick backup (SQLite dev)
python scripts/backup.py --output /tmp/bk --db-url sqlite:///./persona_store.db

# Quick backup (Postgres prod)
python scripts/backup.py --output /var/backups/persona --db-url "$DATABASE_URL" --s3-bucket "$S3_BACKUP_BUCKET"

# List backups
python scripts/backup.py --list --output /var/backups/persona

# Health check
python scripts/healthcheck.py --db-url "$DATABASE_URL"

# Health check (JSON)
python scripts/healthcheck.py --db-url "$DATABASE_URL" --json | jq .

# Validate backup
python scripts/restore.py --validate --backup /var/backups/persona/persona_backup_20240101T020000Z.sql.gz

# Restore from local file
python scripts/restore.py --backup /var/backups/persona/persona_backup_20240101T020000Z.sql.gz --db-url "$DATABASE_URL"

# Restore from S3
python scripts/restore.py --s3-bucket persona-platform-backups --s3-key daily/persona_backup_20240101T020000Z.sql.gz --db-url "$DATABASE_URL"

# Clean up old backups
python scripts/backup.py --cleanup --output /var/backups/persona --keep-days 30

# Trigger manual backup via GitHub Actions
gh workflow run backup.yml
```

### 15.2 Decision Tree: Which Recovery Procedure to Use?

```
Problem detected
       │
       ├── Can you connect to the database?
       │         │
       │   No ───┤── Is there a hot standby?
       │         │         │
       │         │   Yes ──┴──► Section 10: Failover
       │         │
       │         └── No standby ──► Section 7: Restore from backup
       │
       └── Connected, but data is wrong/missing
                 │
                 ├── Do you know the exact time of data loss?
                 │         │
                 │   Yes ──┴──► Section 9: PITR with WAL
                 │
                 └── Unknown ──► Section 7: Restore from last known-good backup
```

### 15.3 Environment Variables Reference

```bash
DATABASE_URL               # SQLAlchemy DB URL
S3_BACKUP_BUCKET           # S3 bucket for backup storage
BACKUP_DIR                 # Local directory for backup files
BACKUP_RETENTION_DAYS      # Days to keep local backups (default: 30)
LOG_FILE                   # Optional log file path
AWS_ACCESS_KEY_ID          # AWS credentials for S3
AWS_SECRET_ACCESS_KEY      # AWS credentials for S3
AWS_DEFAULT_REGION         # AWS region (default: us-east-1)
DB_SUPERUSER_PASSWORD      # Postgres superuser password (for failover/PITR)
PRE_MIGRATION_BACKUP       # Set to "0" to skip pre-migration backup (default: "1")
```

---

## 16. Contact & Escalation

### 16.1 Escalation Matrix

| Severity | Definition | Response Time | Contact |
|---|---|---|---|
| P1 — Critical | DB completely down, data loss risk | 15 minutes | On-call engineer (PagerDuty) |
| P2 — High | Replication down, backup failed | 30 minutes | Platform Engineering team |
| P3 — Medium | Degraded performance, delayed backup | 2 hours | Platform Engineering (Slack) |
| P4 — Low | Non-critical warning, informational | Next business day | GitHub Issue |

### 16.2 Incident Response Process

1. **Detection** — Automated monitoring or user report
2. **Triage** — Run `scripts/healthcheck.py`, check application logs
3. **Containment** — Stop writes if data integrity is at risk
4. **Recovery** — Follow the appropriate runbook in this document
5. **Verification** — Run `scripts/healthcheck.py`, smoke test application
6. **Post-mortem** — Write incident report within 24 hours
7. **Improvement** — Update runbooks and monitoring based on findings

### 16.3 Useful PostgreSQL Diagnostics

```sql
-- Active connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

-- Long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > INTERVAL '5 minutes';

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) AS size
FROM pg_class WHERE relkind = 'r' ORDER BY pg_total_relation_size(oid) DESC LIMIT 20;

-- Replication status
SELECT * FROM pg_stat_replication;

-- WAL archive status
SELECT * FROM pg_stat_archiver;

-- Index bloat
SELECT relname, n_dead_tup, n_live_tup, last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
```

---

*This document is version-controlled in Git. To propose changes, open a pull
request with the `operations` and `documentation` labels.  Major changes must
be reviewed by the Platform Engineering lead before merging.*

*Last tested recovery procedure: 2026-06-11*  
*Next scheduled DR drill: 2026-07-11*

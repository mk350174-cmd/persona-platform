#!/bin/bash
# PostgreSQL Automated Backup Script
# Daily full backup to S3 with gzip compression
# Usage: ./pg_backup.sh
# Environment: DATABASE_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BACKUP_S3_BUCKET

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:=/tmp/persona_backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:=30}"
LOG_FILE="${LOG_FILE:=/var/log/persona_backup.log}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
BACKUP_FILENAME="persona_backup_${TIMESTAMP}.sql.gz"

# Ensure directories exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

log "INFO" "Starting PostgreSQL backup (${TIMESTAMP})"

# Validate environment
if [[ -z "${DATABASE_URL:-}" ]]; then
    log "ERROR" "DATABASE_URL environment variable not set"
    exit 1
fi

if [[ -z "${BACKUP_S3_BUCKET:-}" ]]; then
    log "ERROR" "BACKUP_S3_BUCKET environment variable not set"
    exit 1
fi

# Parse PostgreSQL connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/database
if ! parse_db_url() {
    local db_url="$DATABASE_URL"

    # Remove scheme
    db_url="${db_url#postgresql://}"

    # Extract user and password
    local user_pass="${db_url%%@*}"
    local host_db="${db_url#*@}"

    DB_USER="${user_pass%%:*}"
    DB_PASSWORD="${user_pass#*:}"
    DB_HOST="${host_db%%/*}"
    DB_NAME="${host_db#*/}"

    # Handle port
    if [[ "$DB_HOST" == *":"* ]]; then
        DB_PORT="${DB_HOST##*:}"
        DB_HOST="${DB_HOST%:*}"
    else
        DB_PORT="5432"
    fi

    # Validate
    if [[ -z "$DB_USER" ]] || [[ -z "$DB_HOST" ]] || [[ -z "$DB_NAME" ]]; then
        log "ERROR" "Failed to parse DATABASE_URL"
        return 1
    fi

    return 0
}

if ! parse_db_url; then
    exit 1
fi

log "DEBUG" "Database: user=$DB_USER, host=$DB_HOST:$DB_PORT, database=$DB_NAME"

# Test database connectivity
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
    log "ERROR" "Cannot connect to database at $DB_HOST:$DB_PORT"
    exit 1
fi

log "INFO" "Database connectivity check passed"

# Perform backup
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
log "INFO" "Creating backup: $BACKUP_PATH"

if PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --verbose \
    --no-password \
    --on-conflict-do-nothing \
    | gzip > "$BACKUP_PATH"; then

    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log "INFO" "Backup completed successfully (size: $BACKUP_SIZE)"
else
    log "ERROR" "Backup failed"
    rm -f "$BACKUP_PATH"
    exit 1
fi

# Upload to S3
if ! command -v aws &> /dev/null; then
    log "WARN" "aws CLI not found, skipping S3 upload"
else
    log "INFO" "Uploading backup to S3: s3://${BACKUP_S3_BUCKET}/${BACKUP_FILENAME}"

    if aws s3 cp "$BACKUP_PATH" "s3://${BACKUP_S3_BUCKET}/${BACKUP_FILENAME}" \
        --sse AES256 \
        --metadata "timestamp=${TIMESTAMP},size=${BACKUP_SIZE},database=${DB_NAME}" \
        2>&1 | tee -a "$LOG_FILE"; then

        log "INFO" "S3 upload completed"

        # Clean up local backup after successful upload
        rm -f "$BACKUP_PATH"
        log "INFO" "Local backup file removed"
    else
        log "ERROR" "S3 upload failed (keeping local backup at $BACKUP_PATH)"
        exit 1
    fi
fi

# Clean up old backups (local)
log "INFO" "Cleaning up backups older than $BACKUP_RETENTION_DAYS days"
find "$BACKUP_DIR" -name "persona_backup_*.sql.gz" -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete

log "INFO" "Backup completed successfully"
exit 0

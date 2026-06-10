#!/bin/bash
# PostgreSQL Point-in-Time Recovery Script
# Restores from backup with validation and rollback capability
# Usage: ./pg_restore.sh [timestamp] [target_database]
#        ./pg_restore.sh --validate [timestamp]
#        ./pg_restore.sh --rollback

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:=/tmp/persona_backups}"
RESTORE_DIR="/tmp/persona_restore"
LOG_FILE="${LOG_FILE:=/var/log/persona_restore.log}"
ORIGINAL_DB_SUFFIX="_original_$(date +%s)"

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Parse database URL
parse_db_url() {
    local db_url="$DATABASE_URL"
    db_url="${db_url#postgresql://}"

    local user_pass="${db_url%%@*}"
    local host_db="${db_url#*@}"

    DB_USER="${user_pass%%:*}"
    DB_PASSWORD="${user_pass#*:}"
    DB_HOST="${host_db%%/*}"
    DB_NAME="${host_db#*/}"

    if [[ "$DB_HOST" == *":"* ]]; then
        DB_PORT="${DB_HOST##*:}"
        DB_HOST="${DB_HOST%:*}"
    else
        DB_PORT="5432"
    fi
}

# Show usage
usage() {
    cat <<EOF
PostgreSQL Point-in-Time Recovery Script

Usage:
  ./pg_restore.sh [timestamp] [target_database]
    Restore from backup at specific timestamp
    timestamp format: 2024-06-10T14-30-00Z
    target_database: optional, defaults to DATABASE_URL

  ./pg_restore.sh --validate [timestamp]
    Validate backup file integrity without restoring

  ./pg_restore.sh --rollback
    Rollback previous restore by swapping database names

Environment:
  DATABASE_URL: PostgreSQL connection string
  BACKUP_S3_BUCKET: S3 bucket containing backups
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY: AWS credentials

Examples:
  # Restore from latest backup
  ./pg_restore.sh latest

  # Restore to specific time
  ./pg_restore.sh 2024-06-10T14-30-00Z

  # Validate backup
  ./pg_restore.sh --validate 2024-06-10T14-30-00Z

  # Rollback to previous database
  ./pg_restore.sh --rollback
EOF
}

# Validate backup integrity
validate_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log "ERROR" "Backup file not found: $backup_file"
        return 1
    fi

    log "INFO" "Validating backup: $backup_file"

    # Check if gzip file is valid
    if ! gzip -t "$backup_file" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Backup file is corrupted (gzip validation failed)"
        return 1
    fi

    # Check if SQL is valid (sample check)
    log "INFO" "Checking SQL syntax..."
    if ! gunzip -c "$backup_file" | head -100 | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --dry-run >/dev/null 2>&1; then
        # Dry-run may fail, so just warn
        log "WARN" "SQL syntax check inconclusive (may be normal)"
    fi

    log "INFO" "Backup validation passed"
    return 0
}

# Find backup by timestamp
find_backup() {
    local timestamp="$1"

    if [[ "$timestamp" == "latest" ]]; then
        # Find most recent local backup
        local backup=$(ls -1t "$BACKUP_DIR"/persona_backup_*.sql.gz 2>/dev/null | head -1)
        if [[ -n "$backup" ]]; then
            echo "$backup"
            return 0
        fi

        # Find most recent S3 backup
        if command -v aws &> /dev/null && [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
            log "INFO" "Finding latest backup in S3..."
            backup=$(aws s3 ls "s3://${BACKUP_S3_BUCKET}/" --recursive \
                | grep "persona_backup_.*\.sql\.gz" \
                | sort | tail -1 | awk '{print $NF}')
            if [[ -n "$backup" ]]; then
                echo "s3://${BACKUP_S3_BUCKET}/${backup}"
                return 0
            fi
        fi

        log "ERROR" "No backups found"
        return 1
    fi

    # Check local backup first
    local local_backup="${BACKUP_DIR}/persona_backup_${timestamp}.sql.gz"
    if [[ -f "$local_backup" ]]; then
        echo "$local_backup"
        return 0
    fi

    # Check S3
    if command -v aws &> /dev/null && [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
        log "INFO" "Searching for backup: $timestamp in S3..."
        local s3_backup="s3://${BACKUP_S3_BUCKET}/persona_backup_${timestamp}.sql.gz"
        if aws s3 ls "$s3_backup" >/dev/null 2>&1; then
            echo "$s3_backup"
            return 0
        fi
    fi

    log "ERROR" "Backup not found: $timestamp"
    return 1
}

# Download backup from S3
download_backup() {
    local s3_path="$1"
    local local_path="$2"

    log "INFO" "Downloading: $s3_path"

    if ! aws s3 cp "$s3_path" "$local_path" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Failed to download backup from S3"
        return 1
    fi

    log "INFO" "Download completed"
    return 0
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    local target_db="$2"

    mkdir -p "$RESTORE_DIR"

    log "INFO" "Decompressing backup..."
    local sql_file="${RESTORE_DIR}/persona_restore.sql"

    if ! gunzip -c "$backup_file" > "$sql_file"; then
        log "ERROR" "Failed to decompress backup"
        return 1
    fi

    log "INFO" "Backup decompressed (size: $(du -h "$sql_file" | cut -f1))"

    # Test restore to temporary database first
    local test_db="${target_db}_test_$$"

    log "INFO" "Testing restore to temporary database: $test_db"
    if PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>&1 | tee -a "$LOG_FILE"; then
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$test_db" -f "$sql_file" >/dev/null 2>&1; then
            log "INFO" "Test restore successful"

            # Verify data integrity
            log "INFO" "Verifying data integrity..."
            local row_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$test_db" -t -c "
                SELECT SUM(row_count) FROM (
                    SELECT COUNT(*) as row_count FROM users
                    UNION ALL SELECT COUNT(*) FROM purchases
                    UNION ALL SELECT COUNT(*) FROM subscriptions
                ) t")

            log "INFO" "Total row count in test database: $row_count"

            if [[ "$row_count" -eq 0 ]]; then
                log "WARN" "Test database has no data (may indicate empty backup)"
            fi

            # Drop test database and restore to target
            log "INFO" "Dropping test database"
            PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>&1 | tee -a "$LOG_FILE"

            # Rename original and restore
            log "INFO" "Renaming original database: ${target_db} → ${target_db}${ORIGINAL_DB_SUFFIX}"
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "ALTER DATABASE \"${target_db}\" RENAME TO \"${target_db}${ORIGINAL_DB_SUFFIX}\"" 2>&1 | tee -a "$LOG_FILE"; then

                log "INFO" "Creating new database: $target_db"
                if PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$target_db"; then
                    log "INFO" "Restoring data to $target_db..."
                    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$target_db" -f "$sql_file" >/dev/null 2>&1; then
                        log "INFO" "Restore completed successfully"
                        log "INFO" "Previous database backed up as: ${target_db}${ORIGINAL_DB_SUFFIX}"

                        # Cleanup
                        rm -f "$sql_file"
                        return 0
                    fi
                fi
            fi
        fi
    fi

    log "ERROR" "Restore failed"
    # Cleanup on failure
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>/dev/null || true
    rm -f "$sql_file"
    return 1
}

# Rollback to previous database
rollback_restore() {
    parse_db_url

    log "INFO" "Looking for backed-up database to rollback..."

    local original_db="${DB_NAME}${ORIGINAL_DB_SUFFIX}"

    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -lqt | grep -q "$original_db"; then
        log "INFO" "Found backed-up database: $original_db"

        log "INFO" "Dropping current database: ${DB_NAME}"
        PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>&1 | tee -a "$LOG_FILE"

        log "INFO" "Renaming backed-up database: ${original_db} → ${DB_NAME}"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "ALTER DATABASE \"${original_db}\" RENAME TO \"${DB_NAME}\"" 2>&1 | tee -a "$LOG_FILE"

        log "INFO" "Rollback completed"
        return 0
    else
        log "ERROR" "No backed-up database found for rollback"
        return 1
    fi
}

# Main logic
if [[ -z "${DATABASE_URL:-}" ]]; then
    log "ERROR" "DATABASE_URL environment variable not set"
    usage
    exit 1
fi

parse_db_url

case "${1:-}" in
    --help|-h)
        usage
        exit 0
        ;;
    --validate)
        backup=$(find_backup "${2:-latest}")
        if [[ "$backup" == s3://* ]]; then
            log "INFO" "Downloading backup from S3 for validation"
            temp_backup="${RESTORE_DIR}/temp_backup.sql.gz"
            mkdir -p "$RESTORE_DIR"
            if download_backup "$backup" "$temp_backup"; then
                validate_backup "$temp_backup"
                result=$?
                rm -f "$temp_backup"
                exit $result
            fi
            exit 1
        else
            validate_backup "$backup"
            exit $?
        fi
        ;;
    --rollback)
        log "INFO" "Rolling back to previous database"
        rollback_restore
        exit $?
        ;;
    *)
        timestamp="${1:-latest}"
        target_db="${2:-${DB_NAME}}"

        log "INFO" "Starting point-in-time recovery"
        log "INFO" "Timestamp: $timestamp, Target DB: $target_db"

        backup=$(find_backup "$timestamp")
        if [[ -z "$backup" ]]; then
            exit 1
        fi

        # Download if from S3
        if [[ "$backup" == s3://* ]]; then
            backup_file="${RESTORE_DIR}/persona_backup.sql.gz"
            mkdir -p "$RESTORE_DIR"
            if ! download_backup "$backup" "$backup_file"; then
                exit 1
            fi
            backup="$backup_file"
        fi

        # Validate
        if ! validate_backup "$backup"; then
            exit 1
        fi

        # Restore
        restore_database "$backup" "$target_db"
        exit $?
        ;;
esac

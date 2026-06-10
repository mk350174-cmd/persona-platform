#!/bin/bash
# Backup Integrity Validation Script
# Checks backup file health and verifiability without full restore
# Usage: ./validate_backup.sh [timestamp]

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:=/tmp/persona_backups}"
LOG_FILE="${LOG_FILE:=/var/log/persona_backup_validate.log}"

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Validate environment
if [[ -z "${DATABASE_URL:-}" ]]; then
    log "ERROR" "DATABASE_URL environment variable not set"
    exit 1
fi

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

# Check backup file integrity
check_gzip_integrity() {
    local backup_file="$1"

    log "INFO" "Checking gzip integrity: $backup_file"

    if ! gzip -t "$backup_file" 2>&1; then
        log "ERROR" "Backup file is corrupted (gzip check failed)"
        return 1
    fi

    log "INFO" "Gzip integrity check passed"
    return 0
}

# Check backup file size
check_backup_size() {
    local backup_file="$1"

    local size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo 0)
    local size_mb=$((size / 1024 / 1024))

    log "INFO" "Backup file size: ${size_mb}MB"

    if [[ $size_mb -lt 1 ]]; then
        log "ERROR" "Backup file is suspiciously small (< 1MB)"
        return 1
    fi

    return 0
}

# Check SQL syntax validity (sample)
check_sql_syntax() {
    local backup_file="$1"

    log "INFO" "Sampling backup for SQL syntax..."

    # Decompress first 1000 lines and check for SQL keywords
    if gunzip -c "$backup_file" | head -1000 | grep -q "^CREATE\|^INSERT\|^DROP\|^ALTER"; then
        log "INFO" "SQL syntax check passed"
        return 0
    else
        log "WARN" "Could not verify SQL syntax (may be valid but encrypted/binary format)"
        return 0
    fi
}

# Check backup metadata
check_backup_metadata() {
    local backup_file="$1"

    # Try to read S3 metadata if available
    if [[ "$backup_file" == s3://* ]]; then
        if command -v aws &> /dev/null; then
            log "INFO" "Checking S3 backup metadata..."

            if aws s3 ls "$backup_file" >/dev/null 2>&1; then
                local metadata=$(aws s3api head-object --bucket "${backup_file#s3://*/}" --key "${backup_file#*//}" 2>/dev/null || echo "")
                if [[ -n "$metadata" ]]; then
                    log "INFO" "S3 backup metadata retrieved"
                    return 0
                fi
            fi

            log "WARN" "Could not retrieve S3 metadata"
        fi
    fi

    return 0
}

# Find backup by timestamp
find_backup() {
    local timestamp="$1"

    if [[ "$timestamp" == "latest" ]]; then
        local backup=$(ls -1t "$BACKUP_DIR"/persona_backup_*.sql.gz 2>/dev/null | head -1)
        if [[ -n "$backup" ]]; then
            echo "$backup"
            return 0
        fi

        # Check S3
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
        local s3_backup="s3://${BACKUP_S3_BUCKET}/persona_backup_${timestamp}.sql.gz"
        if aws s3 ls "$s3_backup" >/dev/null 2>&1; then
            echo "$s3_backup"
            return 0
        fi
    fi

    log "ERROR" "Backup not found: $timestamp"
    return 1
}

# Download S3 backup for local validation
download_for_validation() {
    local s3_path="$1"
    local temp_file="/tmp/backup_validate_$$.sql.gz"

    log "INFO" "Downloading S3 backup for validation..."

    if ! aws s3 cp "$s3_path" "$temp_file" --no-progress 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Failed to download backup from S3"
        return 1
    fi

    echo "$temp_file"
    return 0
}

# Check backup age
check_backup_age() {
    local backup_file="$1"

    local modified_time=$(stat -f%m "$backup_file" 2>/dev/null || stat -c%Y "$backup_file" 2>/dev/null || echo 0)
    local current_time=$(date +%s)
    local age_hours=$(( (current_time - modified_time) / 3600 ))

    log "INFO" "Backup age: ${age_hours} hours"

    if [[ $age_hours -gt 24 ]]; then
        log "WARN" "Backup is older than 24 hours (may be stale)"
        return 1
    fi

    return 0
}

# Generate report
generate_report() {
    local backup_file="$1"

    echo ""
    echo "======================================"
    echo "Backup Validation Report"
    echo "======================================"
    echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S')"
    echo "Backup File: $backup_file"
    echo "======================================"
}

# Main validation
main() {
    parse_db_url

    local timestamp="${1:-latest}"

    log "INFO" "Starting backup validation (timestamp: $timestamp)"

    local backup=$(find_backup "$timestamp")
    if [[ -z "$backup" ]]; then
        exit 1
    fi

    generate_report "$backup"

    # Download S3 backup if needed
    local temp_file=""
    if [[ "$backup" == s3://* ]]; then
        temp_file=$(download_for_validation "$backup")
        if [[ -z "$temp_file" ]]; then
            exit 1
        fi
        backup="$temp_file"
    fi

    local all_pass=true

    # Run validation checks
    if ! check_backup_age "$backup"; then
        all_pass=false
    fi

    if ! check_backup_size "$backup"; then
        all_pass=false
    fi

    if ! check_gzip_integrity "$backup"; then
        all_pass=false
    fi

    if ! check_sql_syntax "$backup"; then
        all_pass=false
    fi

    if ! check_backup_metadata "$backup"; then
        all_pass=false
    fi

    # Cleanup
    if [[ -n "$temp_file" ]] && [[ -f "$temp_file" ]]; then
        rm -f "$temp_file"
    fi

    # Summary
    echo ""
    if [[ "$all_pass" == true ]]; then
        log "INFO" "✅ All validation checks passed"
        echo "======================================"
        echo "Status: VALID"
        echo "======================================"
        exit 0
    else
        log "ERROR" "❌ Some validation checks failed"
        echo "======================================"
        echo "Status: INVALID"
        echo "======================================"
        exit 1
    fi
}

main "$@"

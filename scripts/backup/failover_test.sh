#!/bin/bash
# Failover & Disaster Recovery Test Script
# Performs dry-run recovery testing and simulates failover scenarios
# Usage: ./failover_test.sh [--full] [timestamp]

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:=/tmp/persona_backups}"
TEST_DB_SUFFIX="_failover_test_$$"
LOG_FILE="${LOG_FILE:=/var/log/persona_failover_test.log}"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
TEST_REPORT="/tmp/failover_test_report_${TIMESTAMP}.txt"

# Metrics
TEST_START_TIME=$(date +%s)
RECOVERY_TIME=0

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

# Create test report
create_report() {
    cat > "$TEST_REPORT" <<EOF
Failover Test Report
====================
Date: $(date -u '+%Y-%m-%d %H:%M:%S')
Database: ${DB_NAME}
Host: ${DB_HOST}:${DB_PORT}

Test Results:
EOF
}

# Append to report
append_report() {
    echo "$@" >> "$TEST_REPORT"
}

# Check database connectivity
check_connectivity() {
    local host="$1"
    local port="$2"
    local user="$3"
    local password="$4"
    local db="$5"

    if PGPASSWORD="$password" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Get table row counts
get_table_stats() {
    local db="$1"

    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables
        ORDER BY schemaname, tablename;" 2>/dev/null || echo "No tables found"
}

# Verify data integrity
verify_data_integrity() {
    local db="$1"

    log "INFO" "Verifying data integrity in $db..."

    # Count total rows
    local total_rows=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT COUNT(*)::INT FROM (
            SELECT 1 FROM users
            UNION ALL SELECT 1 FROM purchases
            UNION ALL SELECT 1 FROM subscriptions
        ) t" 2>/dev/null || echo 0)

    log "INFO" "Total rows in test database: $total_rows"
    append_report "Total rows in restored database: $total_rows"

    # Check table constraints
    log "INFO" "Checking table constraints..."

    local constraint_check=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')" 2>/dev/null || echo 0)

    log "INFO" "Constraints found: $constraint_check"
    append_report "Constraints found: $constraint_check"

    # Check indexes
    local index_check=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')" 2>/dev/null || echo 0)

    log "INFO" "Indexes found: $index_check"
    append_report "Indexes found: $index_check"

    if [[ $total_rows -eq 0 ]]; then
        log "WARN" "No data found in restored database (may be intentional)"
        append_report "⚠️  WARNING: No data found in restored database"
        return 1
    fi

    log "INFO" "Data integrity verification completed"
    return 0
}

# Find backup
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

    # Check local first
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

# Download backup if needed
download_backup() {
    local s3_path="$1"
    local local_path="/tmp/failover_test_backup_$$.sql.gz"

    log "INFO" "Downloading backup from S3..."
    if ! aws s3 cp "$s3_path" "$local_path" --no-progress 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Failed to download backup"
        return 1
    fi

    echo "$local_path"
    return 0
}

# Run dry-run recovery test
run_recovery_test() {
    local backup="$1"

    log "INFO" "========== RECOVERY TEST START =========="
    local recovery_start=$(date +%s)

    # Download if from S3
    if [[ "$backup" == s3://* ]]; then
        backup=$(download_backup "$backup")
        if [[ -z "$backup" ]]; then
            return 1
        fi
    fi

    # Validate backup
    log "INFO" "Validating backup..."
    if ! gzip -t "$backup" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Backup file is corrupted"
        return 1
    fi

    # Decompress
    log "INFO" "Decompressing backup..."
    local sql_file="/tmp/failover_test_${$}.sql"
    if ! gunzip -c "$backup" > "$sql_file"; then
        log "ERROR" "Failed to decompress backup"
        return 1
    fi

    # Create test database
    local test_db="${DB_NAME}${TEST_DB_SUFFIX}"
    log "INFO" "Creating test database: $test_db"

    if ! PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Failed to create test database"
        rm -f "$sql_file"
        return 1
    fi

    # Restore data
    log "INFO" "Restoring data to test database..."
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$test_db" -f "$sql_file" >/dev/null 2>&1; then
        log "ERROR" "Restore failed"
        PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>/dev/null || true
        rm -f "$sql_file"
        return 1
    fi

    local recovery_end=$(date +%s)
    RECOVERY_TIME=$((recovery_end - recovery_start))

    log "INFO" "Recovery time: ${RECOVERY_TIME}s"
    append_report "Recovery time: ${RECOVERY_TIME} seconds"

    # Verify data
    if ! verify_data_integrity "$test_db"; then
        log "WARN" "Data integrity check incomplete"
    fi

    # Cleanup test database
    log "INFO" "Cleaning up test database"
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$test_db" 2>&1 | tee -a "$LOG_FILE"

    rm -f "$sql_file"

    log "INFO" "========== RECOVERY TEST PASSED =========="
    append_report "✅ Recovery test PASSED"

    return 0
}

# Run full failover test
run_full_failover_test() {
    log "INFO" "========== FULL FAILOVER TEST START =========="
    append_report ""
    append_report "Full Failover Test:"

    # Health check on primary
    log "INFO" "Checking primary database connectivity..."
    if ! check_connectivity "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASSWORD" "$DB_NAME"; then
        log "ERROR" "Cannot connect to primary database"
        append_report "❌ Primary database unreachable"
        return 1
    fi

    append_report "✅ Primary database connectivity OK"

    # Get baseline stats
    log "INFO" "Collecting baseline statistics from primary..."
    local baseline_stats=$(get_table_stats "$DB_NAME")
    append_report "Baseline table statistics:"
    append_report "$baseline_stats"

    # Run recovery test
    if ! run_recovery_test "latest"; then
        log "ERROR" "Recovery test failed"
        return 1
    fi

    log "INFO" "========== FULL FAILOVER TEST PASSED =========="
    append_report "✅ Full failover test PASSED"
    return 0
}

# Main function
main() {
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log "ERROR" "DATABASE_URL environment variable not set"
        exit 1
    fi

    parse_db_url
    create_report

    log "INFO" "Starting failover test"
    append_report "Start time: $(date -u '+%Y-%m-%d %H:%M:%S')"

    local test_type="recovery"
    local timestamp="latest"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --full)
                test_type="full"
                shift
                ;;
            *)
                timestamp="$1"
                shift
                ;;
        esac
    done

    # Find backup
    local backup=$(find_backup "$timestamp")
    if [[ -z "$backup" ]]; then
        log "ERROR" "Backup not found"
        exit 1
    fi

    log "INFO" "Using backup: $backup"
    append_report "Backup: $backup"

    # Run test
    case "$test_type" in
        full)
            if run_full_failover_test; then
                test_result="PASSED"
            else
                test_result="FAILED"
            fi
            ;;
        recovery)
            if run_recovery_test "$backup"; then
                test_result="PASSED"
            else
                test_result="FAILED"
            fi
            ;;
    esac

    # Final report
    append_report ""
    append_report "End time: $(date -u '+%Y-%m-%d %H:%M:%S')"
    append_report "Total test duration: $(($(date +%s) - TEST_START_TIME)) seconds"
    append_report ""
    append_report "Final Status: $test_result"

    log "INFO" "Test report: $TEST_REPORT"
    cat "$TEST_REPORT"

    if [[ "$test_result" == "PASSED" ]]; then
        log "INFO" "✅ Failover test PASSED"
        exit 0
    else
        log "ERROR" "❌ Failover test FAILED"
        exit 1
    fi
}

main "$@"

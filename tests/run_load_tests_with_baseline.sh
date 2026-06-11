#!/bin/bash
# Comprehensive Load Testing Suite with Baseline Metrics Collection
# Runs normal scenario (production baseline) with automatic metrics parsing
# and regression detection
#
# Usage: ./tests/run_load_tests_with_baseline.sh [environment]
# Environment: staging (default), production, custom
#
# Features:
#   - Validates backend is running before tests
#   - Runs normal scenario (50 users, 10 minutes)
#   - Collects detailed metrics (response times, RPS, errors)
#   - Compares against previous baseline
#   - Generates HTML report with graphs
#   - Alerts on metric regressions

set -euo pipefail

# ════════════════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════════════════

ENVIRONMENT="${1:-staging}"
HOST="${HOST:-http://localhost:8000}"
RESULTS_DIR="results"
BASELINE_DIR="results/baselines"
SCRIPTS_DIR="scripts"
TESTS_DIR="tests"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TIMESTAMP_READABLE=$(date '+%Y-%m-%d %H:%M:%S')

# Locust configuration for normal scenario (production baseline)
USERS=50
SPAWN_RATE=5
DURATION=10  # minutes
TEST_NAME="normal_baseline"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ════════════════════════════════════════════════════════════════════════════
# Functions
# ════════════════════════════════════════════════════════════════════════════

log_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
}

log_info() {
    echo -e "${CYAN}ℹ  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check backend connectivity
check_backend() {
    log_info "Checking backend connectivity..."

    if ! command_exists curl; then
        log_error "curl not found. Please install curl."
        exit 1
    fi

    local max_retries=5
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -s -f "${HOST}/health" > /dev/null 2>&1; then
            log_success "Backend is running at ${HOST}"
            return 0
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            log_warning "Backend not responding (attempt $retry/$max_retries), retrying in 2 seconds..."
            sleep 2
        fi
    done

    log_error "Backend is not responding at ${HOST}"
    log_info "Please start the backend with: python -m uvicorn api.main:app --reload --port 8000"
    exit 1
}

# Check if Locust is installed
check_locust() {
    log_info "Checking Locust installation..."

    if ! command_exists locust; then
        log_error "Locust not installed"
        log_info "Install with: pip install locust"
        exit 1
    fi

    local version=$(locust --version 2>/dev/null | awk '{print $NF}')
    log_success "Locust ${version} is installed"
}

# Check if Python metrics module is available
check_python_deps() {
    log_info "Checking Python dependencies..."

    if ! python3 -c "import pandas" 2>/dev/null; then
        log_warning "pandas not installed (optional, needed for advanced analysis)"
        log_info "Install with: pip install pandas matplotlib"
    fi
}

# Create directories
setup_directories() {
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$BASELINE_DIR"
    mkdir -p "$RESULTS_DIR/reports"
}

# Run load test with Locust
run_load_test() {
    log_header "Running Normal Load Test (Production Baseline)"
    log_info "Configuration:"
    log_info "  Users: $USERS"
    log_info "  Spawn Rate: $SPAWN_RATE/sec"
    log_info "  Duration: $DURATION minutes"
    log_info "  Target: $HOST"
    log_info "  Environment: $ENVIRONMENT"
    echo ""

    local csv_prefix="${RESULTS_DIR}/${TEST_NAME}_${TIMESTAMP}"

    # Run Locust
    locust \
        -f "${TESTS_DIR}/load_test_platform.py" \
        --host="${HOST}" \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "${DURATION}m" \
        --csv="${csv_prefix}" \
        --headless \
        --stop-timeout 30 \
        2>&1 | tee "${RESULTS_DIR}/${TEST_NAME}_${TIMESTAMP}.log" | tail -30

    echo ""
    log_success "Load test completed"

    # Store CSV prefix for later processing
    echo "${csv_prefix}" > "${RESULTS_DIR}/.last_test"
}

# Parse metrics from Locust CSV output
parse_metrics() {
    local csv_stats="${1}_stats.csv"

    if [ ! -f "$csv_stats" ]; then
        log_error "Stats file not found: $csv_stats"
        return 1
    fi

    log_header "Parsing Load Test Metrics"

    # Extract metrics using awk/grep
    local metrics_json="${RESULTS_DIR}/${TEST_NAME}_${TIMESTAMP}_metrics.json"

    python3 << 'PYTHON_EOF'
import csv
import sys
import json
from collections import defaultdict

csv_file = sys.argv[1]
metrics = {}

try:
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        aggregated = {}

        for row in reader:
            if row['Name'] == 'Aggregated':
                aggregated = row
                break

        if aggregated:
            # Convert numeric fields
            metrics = {
                'timestamp': sys.argv[2],
                'total_requests': int(aggregated.get('# requests', 0)),
                'total_failures': int(aggregated.get('# failures', 0)),
                'error_rate_pct': float(aggregated.get('# failures', 0)) / max(1, int(aggregated.get('# requests', 1))) * 100,
                'p50_ms': float(aggregated.get('Median response time', 0)),
                'p95_ms': float(aggregated.get('95%', 0)),
                'p99_ms': float(aggregated.get('99%', 0)),
                'avg_response_time_ms': float(aggregated.get('Average response time', 0)),
                'min_response_time_ms': float(aggregated.get('Min response time', 0)),
                'max_response_time_ms': float(aggregated.get('Max response time', 0)),
                'rps': float(aggregated.get('Requests/s', 0)),
            }

            # Calculate metrics if not in CSV
            if metrics['total_requests'] > 0:
                metrics['error_rate_pct'] = (metrics['total_failures'] / metrics['total_requests']) * 100

            print(json.dumps(metrics, indent=2))
        else:
            print("Error: Could not find aggregated metrics", file=sys.stderr)
            sys.exit(1)

except Exception as e:
    print(f"Error parsing CSV: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF

    return $?
}

# Compare against baseline expectations
compare_to_baseline() {
    local metrics_json="$1"
    local baseline_file="${BASELINE_DIR}/baseline.json"

    log_header "Comparing Against Baseline"

    if [ ! -f "$baseline_file" ]; then
        log_warning "No previous baseline found"
        log_info "Creating initial baseline at ${baseline_file}"
        cp "$metrics_json" "$baseline_file"
        return 0
    fi

    python3 "${TESTS_DIR}/baseline_metrics.py" \
        --current "$metrics_json" \
        --baseline "$baseline_file" \
        --output "${RESULTS_DIR}/regression_report_${TIMESTAMP}.html"
}

# Generate summary report
generate_summary() {
    local csv_stats="${1}_stats.csv"
    local test_log="${RESULTS_DIR}/${TEST_NAME}_${TIMESTAMP}.log"

    log_header "Performance Summary"

    if [ ! -f "$csv_stats" ]; then
        log_warning "Stats file not found for summary"
        return 1
    fi

    python3 << 'PYTHON_EOF'
import csv
import sys

csv_file = sys.argv[1]

print("")
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)

    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  Response Time Metrics (ms)                                │")
    print("├─────────────────────────────────────────────────────────────┤")

    for row in reader:
        if row['Name'] == 'Aggregated':
            p50 = float(row.get('Median response time', 0))
            p95 = float(row.get('95%', 0))
            p99 = float(row.get('99%', 0))
            max_rt = float(row.get('Max response time', 0))

            print(f"│  p50 (Median):   {p50:>8.0f} ms", end="")
            if p50 < 200:
                print("  ✅ Excellent")
            else:
                print("")

            print(f"│  p95:            {p95:>8.0f} ms", end="")
            if p95 < 500:
                print("  ✅ Good")
            elif p95 < 1000:
                print("  ⚠️  Watch")
            else:
                print("  ❌ Needs work")

            print(f"│  p99:            {p99:>8.0f} ms", end="")
            if p99 < 1000:
                print("  ✅ Good")
            elif p99 < 2000:
                print("  ⚠️  Watch")
            else:
                print("  ❌ Needs work")

            print(f"│  Max:            {max_rt:>8.0f} ms")

    f.seek(0)
    reader = csv.DictReader(f)

    print("├─────────────────────────────────────────────────────────────┤")
    print("│  Throughput & Errors                                       │")
    print("├─────────────────────────────────────────────────────────────┤")

    for row in reader:
        if row['Name'] == 'Aggregated':
            total_reqs = int(row.get('# requests', 0))
            total_fails = int(row.get('# failures', 0))
            rps = float(row.get('Requests/s', 0))
            error_rate = (total_fails / max(1, total_reqs)) * 100

            print(f"│  Total Requests: {total_reqs:>8} ")
            print(f"│  Total Failures: {total_fails:>8} ({error_rate:.2f}%)", end="")
            if error_rate < 1.0:
                print("  ✅ Excellent")
            elif error_rate < 2.0:
                print("  ✅ Good")
            elif error_rate < 5.0:
                print("  ⚠️  Acceptable")
            else:
                print("  ❌ High")

            print(f"│  RPS:            {rps:>8.2f} req/sec")

print("└─────────────────────────────────────────────────────────────┘")
print("")
PYTHON_EOF
}

# Check for performance alerts
check_performance_alerts() {
    local metrics_json="$1"

    log_header "Performance Alerts"

    python3 "${TESTS_DIR}/baseline_metrics.py" \
        --check-alerts "$metrics_json" \
        --output "${RESULTS_DIR}/alerts_${TIMESTAMP}.json"
}

# ════════════════════════════════════════════════════════════════════════════
# Main Execution
# ════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    log_header "Load Testing Suite v1.0"
    log_info "Environment: $ENVIRONMENT"
    log_info "Started: $TIMESTAMP_READABLE"
    echo ""

    # Pre-flight checks
    check_locust
    check_python_deps
    check_backend
    setup_directories

    echo ""

    # Run load test
    run_load_test

    # Parse results
    csv_prefix=$(cat "${RESULTS_DIR}/.last_test")
    if [ -z "$csv_prefix" ]; then
        log_error "Could not determine test results location"
        exit 1
    fi

    # Generate summary
    echo ""
    generate_summary "$csv_prefix"

    # Compare to baseline
    echo ""
    metrics_json="${RESULTS_DIR}/${TEST_NAME}_${TIMESTAMP}_metrics.json"
    if parse_metrics "$csv_prefix" > "$metrics_json"; then
        compare_to_baseline "$metrics_json"
    fi

    # Check alerts
    echo ""
    if [ -f "$metrics_json" ]; then
        check_performance_alerts "$metrics_json"
    fi

    # Final summary
    echo ""
    log_header "Test Complete"
    log_info "Results saved to:"
    log_info "  CSV: ${csv_prefix}_*.csv"
    log_info "  Log: ${csv_prefix}.log"
    log_info "  Metrics: ${metrics_json}"
    log_info "  Report: ${RESULTS_DIR}/reports/"
    echo ""
    log_success "Baseline metrics collection complete!"
    echo ""
}

# Run main function
main "$@"

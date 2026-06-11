#!/bin/bash
################################################################################
# run_integration_tests.sh — Comprehensive Integration Test Suite Runner
#
# Runs all integration tests against a live backend with health checks,
# optional backend startup, result collection, and summary reporting.
#
# Usage:
#   ./tests/run_integration_tests.sh [OPTIONS]
#
# Options:
#   --url URL              Target backend URL (default: http://localhost:8000)
#   --start-backend        Start backend via docker-compose if not running
#   --skip-health-check    Skip health check before running tests
#   --suite SUITE          Run specific test suite (backend, websocket, all)
#   --json-output FILE     Save JSON results to file
#   --html-output FILE     Generate HTML report (requires integration_test_report.py)
#   --help                 Show this help message
#
# Example:
#   ./tests/run_integration_tests.sh --url http://localhost:8000 --start-backend
#   ./tests/run_integration_tests.sh --suite backend --json-output results.json
#
################################################################################

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
START_BACKEND=false
SKIP_HEALTH_CHECK=false
TEST_SUITE="all"
JSON_OUTPUT=""
HTML_OUTPUT=""
RESULTS_DIR="${REPO_ROOT}/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    head -30 "$0" | tail -27
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            TARGET_URL="$2"
            shift 2
            ;;
        --start-backend)
            START_BACKEND=true
            shift
            ;;
        --skip-health-check)
            SKIP_HEALTH_CHECK=true
            shift
            ;;
        --suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        --json-output)
            JSON_OUTPUT="$2"
            shift 2
            ;;
        --html-output)
            HTML_OUTPUT="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Extract host and port from URL
BACKEND_HOST=$(echo "$TARGET_URL" | sed 's#.*://##' | cut -d: -f1)
BACKEND_PORT=$(echo "$TARGET_URL" | sed 's#.*://##' | cut -d: -f2 || echo "80")
if [[ "$BACKEND_PORT" == "$BACKEND_HOST" ]]; then
    BACKEND_PORT="80"
fi

log_info "=== Persona Platform Integration Test Suite ==="
log_info "Target URL: $TARGET_URL"
log_info "Test Suite: $TEST_SUITE"
log_info "Timestamp: $TIMESTAMP"

# Function to check if backend is running
check_backend_running() {
    local url="$1"
    if curl -s -f -m 5 "${url}/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start backend via docker-compose
start_backend() {
    log_info "Attempting to start backend via docker-compose..."

    if [ ! -f "$REPO_ROOT/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found in $REPO_ROOT"
        return 1
    fi

    cd "$REPO_ROOT"
    if docker-compose up -d; then
        log_success "Backend started"
        # Wait for backend to be ready
        log_info "Waiting for backend to be ready..."
        for i in {1..30}; do
            if check_backend_running "$TARGET_URL"; then
                log_success "Backend is ready"
                sleep 2
                return 0
            fi
            echo -n "."
            sleep 1
        done
        log_error "Backend did not become ready within 30 seconds"
        return 1
    else
        log_error "Failed to start backend via docker-compose"
        return 1
    fi
}

# Step 1: Check backend connectivity
log_info "Step 1: Checking backend connectivity..."
if ! check_backend_running "$TARGET_URL"; then
    log_warning "Backend not running at $TARGET_URL"

    if [ "$START_BACKEND" = true ]; then
        if ! start_backend; then
            log_error "Failed to start backend. Exiting."
            exit 1
        fi
    else
        log_error "Backend is not running. Use --start-backend to auto-start."
        exit 1
    fi
else
    log_success "Backend is running and responding"
fi

# Step 2: Run health check (unless skipped)
if [ "$SKIP_HEALTH_CHECK" = false ]; then
    log_info "Step 2: Running detailed health checks..."

    if [ -x "$REPO_ROOT/scripts/validate_backend_health.sh" ]; then
        if ! "$REPO_ROOT/scripts/validate_backend_health.sh" --url "$TARGET_URL"; then
            log_warning "Some health checks failed, but continuing with tests..."
        fi
    else
        log_info "Health check script not found, skipping detailed checks"
    fi
else
    log_info "Step 2: Health checks skipped"
fi

# Step 3: Run pytest with appropriate suite
log_info "Step 3: Running pytest integration tests..."

cd "$REPO_ROOT"

# Determine pytest command based on suite selection
PYTEST_CMD="pytest"
PYTEST_ARGS="-v --tb=short"

case $TEST_SUITE in
    backend)
        PYTEST_ARGS="$PYTEST_ARGS tests/test_backend_integration.py"
        ;;
    websocket)
        PYTEST_ARGS="$PYTEST_ARGS tests/test_websocket_integration.py"
        ;;
    all)
        PYTEST_ARGS="$PYTEST_ARGS tests/test_backend_integration.py tests/test_websocket_integration.py"
        ;;
    *)
        log_error "Unknown test suite: $TEST_SUITE"
        exit 1
        ;;
esac

# Add JSON output if requested
if [ -n "$JSON_OUTPUT" ]; then
    PYTEST_ARGS="$PYTEST_ARGS --json-report --json-report-file=$JSON_OUTPUT"
fi

# Export target URL for tests to use
export TEST_BACKEND_URL="$TARGET_URL"

# Run pytest
if $PYTEST_CMD $PYTEST_ARGS; then
    PYTEST_EXIT_CODE=0
    log_success "All tests passed!"
else
    PYTEST_EXIT_CODE=$?
    log_warning "Some tests failed (exit code: $PYTEST_EXIT_CODE)"
fi

# Step 4: Parse and display results
log_info "Step 4: Analyzing results..."

# Try to parse pytest JSON output if available
if [ -n "$JSON_OUTPUT" ] && [ -f "$JSON_OUTPUT" ]; then
    log_info "Parsing JSON results from $JSON_OUTPUT..."

    # Extract summary statistics using Python
    python3 << PYTHON_EOF
import json
import sys

try:
    with open("$JSON_OUTPUT", "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)

    print(f"\nTest Results Summary:")
    print(f"  Total:   {total}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")

    if failed > 0:
        print(f"\nFailed tests:")
        for test in data.get("tests", []):
            if test.get("outcome") == "failed":
                print(f"  - {test.get('name')}")
                if test.get("call", {}).get("longrepr"):
                    print(f"    {test['call']['longrepr'][:100]}...")

except Exception as e:
    print(f"Warning: Could not parse JSON results: {e}", file=sys.stderr)
PYTHON_EOF
fi

# Step 5: Generate HTML report if requested
if [ -n "$HTML_OUTPUT" ]; then
    log_info "Step 5: Generating HTML report..."

    if [ -f "$REPO_ROOT/tests/integration_test_report.py" ]; then
        if [ -n "$JSON_OUTPUT" ] && [ -f "$JSON_OUTPUT" ]; then
            python3 "$REPO_ROOT/tests/integration_test_report.py" \
                --json-input "$JSON_OUTPUT" \
                --output "$HTML_OUTPUT" \
                --title "Integration Test Report - $TIMESTAMP"

            if [ -f "$HTML_OUTPUT" ]; then
                log_success "HTML report generated: $HTML_OUTPUT"
            else
                log_warning "Failed to generate HTML report"
            fi
        else
            log_warning "JSON output file not found, cannot generate HTML report"
        fi
    else
        log_warning "integration_test_report.py not found"
    fi
else
    log_info "Step 5: HTML report generation skipped"
fi

# Final summary
echo ""
log_info "=== Test Execution Complete ==="
log_info "Summary:"
log_info "  Backend URL: $TARGET_URL"
log_info "  Test Suite: $TEST_SUITE"
log_info "  Timestamp: $TIMESTAMP"
[ -n "$JSON_OUTPUT" ] && log_info "  JSON Results: $JSON_OUTPUT"
[ -n "$HTML_OUTPUT" ] && log_info "  HTML Report: $HTML_OUTPUT"
echo ""

# Exit with appropriate code
exit $PYTEST_EXIT_CODE

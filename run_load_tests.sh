#!/bin/bash
# Run comprehensive payment system load tests
# Usage: ./run_load_tests.sh [scenario]
# Scenarios: light, normal, heavy, spike, all

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST="${HOST:-http://localhost:8000}"
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Payment System Load Testing Suite (H86)              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Target: $HOST"
echo "Results: $RESULTS_DIR"
echo ""

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}❌ Locust not installed. Install with: pip install locust${NC}"
    exit 1
fi

# Function to run a load test scenario
run_scenario() {
    local scenario=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4

    echo -e "${YELLOW}📊 Running $scenario ($users users, $duration minutes)...${NC}"

    locust -f tests/load_test_payments.py \
        --host="$HOST" \
        --users "$users" \
        --spawn-rate "$spawn_rate" \
        --run-time "${duration}m" \
        --csv="$RESULTS_DIR/${scenario}_${TIMESTAMP}" \
        --headless \
        --stop-timeout 30 \
        2>&1 | tail -20

    echo -e "${GREEN}✅ $scenario complete${NC}"
    echo ""
}

# Run scenarios based on argument
case "${1:-all}" in
    light)
        echo -e "${BLUE}Light Load Test (Baseline)${NC}"
        run_scenario "light_load" 20 2 5
        ;;

    normal)
        echo -e "${BLUE}Normal Load Test${NC}"
        run_scenario "normal_load" 50 5 10
        ;;

    heavy)
        echo -e "${BLUE}Heavy Load Test${NC}"
        run_scenario "heavy_load" 100 10 10
        ;;

    spike)
        echo -e "${BLUE}Spike Load Test${NC}"
        run_scenario "spike_load" 200 50 5
        ;;

    all)
        echo -e "${BLUE}Full Load Test Suite (30 minutes total)${NC}"
        echo ""

        run_scenario "light_load" 20 2 5
        sleep 30

        run_scenario "normal_load" 50 5 10
        sleep 30

        run_scenario "heavy_load" 100 10 10
        sleep 30

        run_scenario "spike_load" 200 50 5

        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ Full load test suite complete!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "Results saved to: $RESULTS_DIR"
        echo ""
        echo "Analyze results with:"
        echo "  python tests/analyze_load_results.py $RESULTS_DIR"
        ;;

    *)
        echo -e "${RED}Unknown scenario: $1${NC}"
        echo ""
        echo "Usage: $0 [scenario]"
        echo "Scenarios:"
        echo "  light   - Light load baseline (20 users, 5 min)"
        echo "  normal  - Normal load test (50 users, 10 min)"
        echo "  heavy   - Heavy load test (100 users, 10 min)"
        echo "  spike   - Spike load test (200 users, 5 min)"
        echo "  all     - Run all scenarios (30 min total) [default]"
        echo ""
        echo "Examples:"
        echo "  ./run_load_tests.sh light"
        echo "  ./run_load_tests.sh all"
        echo "  HOST=http://prod.example.com ./run_load_tests.sh normal"
        exit 1
        ;;
esac

exit 0

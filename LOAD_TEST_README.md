# Load Testing Infrastructure — Quick Start

## 🚀 30-Second Quick Start

```bash
# 1. Start API (terminal 1)
cd /home/user/persona-platform
python -m uvicorn api.main:app --reload --port 8000

# 2. Run light load test (terminal 2)
./run_load_tests.sh light

# 3. View results (terminal 3)
python tests/analyze_load_results.py results/
```

## 📊 Available Load Tests

### Single Scenario Tests

```bash
# Light load (20 users, 5 min) - baseline
./run_load_tests.sh light

# Normal load (50 users, 10 min) - typical production
./run_load_tests.sh normal

# Heavy load (100 users, 10 min) - peak traffic
./run_load_tests.sh heavy

# Spike load (200 users, 5 min) - traffic spike handling
./run_load_tests.sh spike
```

### Full Test Suite

```bash
# All scenarios sequentially (30 minutes total)
./run_load_tests.sh all
```

### Custom Tests

```bash
# Direct Locust command (50 users, 5 minutes)
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=5m \
  --headless \
  --csv=results/custom_run
```

## 📈 Distributed Load Testing (1000+ users)

```bash
# Start distributed setup with master + 3 workers
docker-compose -f docker-compose.load-test.yml up -d

# Access Locust UI
open http://localhost:8089

# Set desired users in UI and start test

# View Grafana dashboard
open http://localhost:3000 (admin/admin)

# Monitor logs
docker-compose -f docker-compose.load-test.yml logs -f locust-master

# Stop
docker-compose -f docker-compose.load-test.yml down
```

## 📋 Performance Targets

| Metric | Light | Normal | Heavy | Spike |
|--------|-------|--------|-------|-------|
| **p95 Response** | <200ms | <500ms | <800ms | <1.5s |
| **p99 Response** | <500ms | <1s | <2s | <3s |
| **Error Rate** | <1% | <1% | <2% | <5% |
| **Throughput** | 5+ RPS | 15+ RPS | 50+ RPS | 100+ RPS |

## 📊 Analyzing Results

```bash
# Automatic analysis with recommendations
python tests/analyze_load_results.py results/

# View CSV files directly
cat results/light_load_*_stats.csv | column -t -s,

# Extract slow requests (>500ms)
awk -F',' '$3 > 500 { print $0 }' results/*_response_times.csv | head -10

# View failures
cat results/*_failures.csv
```

## 🔧 Prerequisites

```bash
# Install dependencies
pip install locust[fast] pandas matplotlib

# Verify Locust
locust --version

# Check Python version (3.8+)
python --version
```

## 📚 Full Documentation

See [LOAD_TESTING_GUIDE.md](./LOAD_TESTING_GUIDE.md) for:
- Detailed setup instructions
- Understanding metrics and results
- Performance optimization guide
- Troubleshooting common issues
- CI/CD integration details

## 🎯 Common Tasks

### Run Weekly Load Test

```bash
# On staging
HOST=http://staging-api.example.com ./run_load_tests.sh normal
```

### Compare Performance

```bash
# Save baseline
cp results/normal_load_*_stats.csv results/baseline.csv

# Run test and compare
./run_load_tests.sh normal

# Analyze
python tests/analyze_load_results.py results/ --baseline=results/baseline.csv
```

### Monitor Real-Time

During test execution:

```bash
# Terminal: Watch system resources
watch -n 1 'free -h && echo "---" && top -b -n 1 | head -5'

# Terminal: Monitor connections
watch -n 1 'netstat -an | grep ESTABLISHED | wc -l'

# Terminal: View API logs
docker logs persona-api -f | grep -E 'ERROR|WARN'
```

### Debug Failures

```bash
# Find slowest requests
python3 << 'EOF'
import csv
from pathlib import Path

stats_file = list(Path('results').glob('*_response_times.csv'))[0]
with open(stats_file) as f:
    reader = csv.DictReader(f)
    rows = sorted(
        reader,
        key=lambda r: float(r['Average Response Time'] or 0),
        reverse=True
    )
    for row in rows[:10]:
        print(f"{row['Name']:40} {row['Average Response Time']:>8}ms")
EOF
```

## ⚙️ Configuration

### Environment Variables

```bash
# Target API server
export HOST=http://localhost:8000

# Locust settings
export LOCUST_LOGLEVEL=INFO

# Load test parameters
export LOAD_TEST_USERS=100
export LOAD_TEST_SPAWN_RATE=10
export LOAD_TEST_DURATION=10m
```

### Custom Load Profiles

Edit `tests/load_test_platform.py` to:
- Adjust task weights (what % of users do each action)
- Change think time between actions
- Add new test scenarios
- Modify performance thresholds

## 🐛 Troubleshooting

### "Connection refused"
```bash
# Ensure API is running on port 8000
ps aux | grep uvicorn
# If not running:
python -m uvicorn api.main:app --reload --port 8000
```

### "Too many open files"
```bash
# Increase file descriptor limit
ulimit -n 65536
```

### High error rates
```bash
# Check API logs
docker logs persona-api | tail -50

# Reduce load
./run_load_tests.sh light

# Check database
psql -U persona persona_hub -c "SELECT count(*) FROM pg_stat_activity;"
```

### Out of memory
```bash
# Use fewer concurrent users
locust -f tests/load_test_platform.py --users=20
```

## 📌 Results Location

```bash
results/
├── light_load_*.csv          # Stats/failures/response times
├── normal_load_*.csv
├── heavy_load_*.csv
├── spike_load_*.csv
├── analysis_report.txt       # Summary analysis
└── load_test.log             # Execution log
```

## 📞 Next Steps

1. **Review** [LOAD_TESTING_GUIDE.md](./LOAD_TESTING_GUIDE.md) for comprehensive guide
2. **Run** a light test to verify setup
3. **Analyze** results and identify bottlenecks
4. **Optimize** based on findings
5. **Schedule** regular tests in CI/CD (see `.github/workflows/load-test.yml`)

---

**Questions?** Check the detailed guide or create an issue with:
- Load test scenario you ran
- Results CSV files
- Error messages
- System info (OS, Python version, Locust version)

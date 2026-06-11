# Load Testing Guide — Persona Platform

## Overview

This guide covers load testing infrastructure for the Persona Platform targeting **100+ concurrent users** with production-ready metrics collection and analysis.

**Key Documents:**
- `tests/load_test_platform.py` — Core platform load tests (catalog, chat, analytics)
- `tests/load_test_payments.py` — Payment system load tests (checkout, billing)
- `tests/analyze_load_results.py` — Result analysis and reporting
- `run_load_tests.sh` — Shell script to run all scenarios
- `.github/workflows/load-test.yml` — CI/CD integration (weekly on staging)
- `docker-compose.load-test.yml` — Distributed load generation

---

## Prerequisites

### Required Software

```bash
# Python 3.8+
python3 --version

# Locust (pip install)
pip install locust>=2.15.0

# Optional: faster HTTP client
pip install locust[fast]

# Optional: result visualization
pip install matplotlib numpy pandas
```

### Optional: Docker (for distributed testing)

```bash
docker --version
docker-compose --version
```

### System Requirements

- **Minimum:** 4GB RAM, 2 CPU cores
- **Recommended:** 8GB RAM, 4+ CPU cores
- **For 1000+ users:** Use distributed mode (multi-worker setup)

---

## Quick Start (30 seconds)

### 1. Start the API

```bash
# Terminal 1: Start API server
cd /home/user/persona-platform
python -m uvicorn api.main:app --reload --port 8000
# or
docker-compose up
```

### 2. Run Light Load Test

```bash
# Terminal 2: Run load test
cd /home/user/persona-platform
./run_load_tests.sh light
```

**Expected output:**
```
🚀 Platform Load Test Started
Target: http://localhost:8000
...
✅ light complete
```

### 3. View Results

```bash
python tests/analyze_load_results.py results/
```

**Expected output:**
```
📊 Load Test Results Analyzer
Light Load Results
==================================================
Requests: 2,145 | Failures: 12
Error Rate: 0.56%
RPS: 7.15 requests/sec
Response Times:
  - Median: 145ms
  - p95:    285ms
  - p99:    450ms
  - Max:    2150ms
```

---

## Test Scenarios

### Overview

| Scenario | Users | Duration | Spawn Rate | Use Case |
|----------|-------|----------|-----------|----------|
| **Light** | 20 | 5 min | 2/sec | Baseline (dev/staging) |
| **Normal** | 50 | 10 min | 5/sec | Expected production load |
| **Heavy** | 100 | 10 min | 10/sec | Peak load test |
| **Spike** | 200 | 5 min | 50/sec | Traffic spike handling |
| **All** | All | 30 min | Varies | Full suite (CI/CD) |

### Running Individual Scenarios

```bash
# Light load (20 users, 5 minutes)
./run_load_tests.sh light

# Normal load (50 users, 10 minutes)
./run_load_tests.sh normal

# Heavy load (100 users, 10 minutes)
./run_load_tests.sh heavy

# Spike load (200 users, 5 minutes)
./run_load_tests.sh spike

# All scenarios (30 minutes total)
./run_load_tests.sh all

# Custom Locust command
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m \
  --headless \
  --csv=results/custom_test
```

### Targeting Different Endpoints

```bash
# Payment system only
./run_load_tests.sh payment

# Chat endpoints only
locust -f tests/load_test_platform.py:ChatTasks \
  --host=http://localhost:8000 \
  --users=50

# Analytics endpoints only
locust -f tests/load_test_platform.py:AnalyticsTasks \
  --host=http://localhost:8000 \
  --users=30
```

---

## Performance Targets

### Response Time SLOs

| Endpoint | p50 | p95 | p99 | p99.9 |
|----------|-----|-----|-----|-------|
| **GET /personas** | <50ms | <200ms | <500ms | <1s |
| **GET /personas/{id}** | <30ms | <150ms | <400ms | <800ms |
| **POST /chat/{id}** | <500ms | <1s | <2s | <5s |
| **GET /analytics/dashboard** | <300ms | <800ms | <2s | <5s |
| **WebSocket /ws/chat** | <50ms latency | <150ms | <300ms | <1s |

### Error Rate SLOs

- **Normal operation:** <1% error rate
- **Heavy load:** <2% error rate
- **Spike:** <5% error rate

### Throughput Targets

| Load Level | Min RPS | Expected RPS |
|-----------|---------|--------------|
| Light (20 users) | 5 | 10-15 |
| Normal (50 users) | 20 | 25-40 |
| Heavy (100 users) | 50 | 80-120 |
| Spike (200 users) | 100 | 150-250 |

### Concurrent Connection Limits

- **HTTP/1.1 connections:** 100+ concurrent
- **WebSocket connections:** 100+ concurrent
- **Database connections:** 20-50 (configurable)
- **Memory per user:** ~1-2MB

---

## Step-by-Step: Running and Analyzing Tests

### Step 1: Prepare Environment

```bash
# Create results directory
mkdir -p /home/user/persona-platform/results

# Verify API is running
curl http://localhost:8000/health
# Expected: 200 OK {"status":"healthy"}

# (Optional) Monitor API in separate terminal
watch 'curl -s http://localhost:8000/health | jq'
```

### Step 2: Run Load Test

```bash
cd /home/user/persona-platform

# Run light test with output capture
./run_load_tests.sh light 2>&1 | tee results/light_run.log

# Or: verbose Locust with live dashboard
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=10m \
  --csv=results/test_run
  # Then open http://localhost:8089 for live dashboard
```

### Step 3: Collect Results

Results are automatically saved to `results/` directory:

```bash
ls -lh results/
# light_load_20260611_150000_stats.csv
# light_load_20260611_150000_failures.csv
# light_load_20260611_150000_response_times.csv
```

### Step 4: Analyze Results

```bash
# Automatic analysis
python tests/analyze_load_results.py results/ > results/analysis.txt

# Generate comparison report
python tests/analyze_load_results.py results/ \
  --baseline=results/baseline.json \
  --output=results/regression_report.html
```

### Step 5: Debug Failures (if any)

```bash
# View failed requests
grep "FAIL" results/*_failures.csv

# Extract slow requests
awk -F',' '$3 > 500 { print $0 }' results/*_response_times.csv | head -20

# Check API logs
docker logs persona-api | grep ERROR
# or tail application logs
tail -f /var/log/persona-api.log
```

---

## Interpreting Results

### Key Metrics

#### 1. Response Time Percentiles

```
Median (p50):  150ms   ✅ Good — typical response time
p95:           400ms   ✅ Good — 95% of users wait <400ms
p99:           900ms   ⚠️  Watch — 1% of users wait >900ms
Max:           5200ms  ⚠️  Investigate — outlier spike
```

**Interpretation:**
- **p50 < 200ms:** Excellent response times
- **p95 < 500ms:** Good SLO target
- **p99 > 2000ms:** Indicates need for optimization
- **Max >> p99:** Look for occasional outlier spikes

#### 2. Error Rate

```
Total Requests:  10,450
Total Failures:  85
Error Rate:      0.81%  ✅ Acceptable (<1%)
```

**By status code:**
```
200 OK:              9,850 (94.3%)
503 Service Unavailable: 45 (0.43%)
500 Internal Server Error: 40 (0.38%)
```

**Interpretation:**
- **0-1%:** Normal, production-ready
- **1-2%:** Acceptable under stress
- **>2%:** Indicates capacity issues

#### 3. Throughput (RPS)

```
Total Requests:   10,450
Duration:         600 sec (10 min)
RPS:              17.4 requests/sec  ✅ Good
```

**For concurrent users:**
```
50 users @ 17.4 RPS = ~0.35 req/user/sec (realistic)
```

#### 4. Concurrent Connections

Monitor during test:
```bash
netstat -an | grep ESTABLISHED | wc -l
# Should increase with user ramp-up, stay stable during load
```

### Example: Light Load Results

**Baseline scenario (20 users):**
```
Requests:        2,145
Failures:        12 (0.56% error rate)
RPS:             7.15
p50:             145ms
p95:             285ms
p99:             450ms
Max:             2150ms
```

**Assessment:** ✅ **PASS** — All metrics within targets

### Example: Heavy Load Results

**Stress test (100 users):**
```
Requests:        8,750
Failures:        95 (1.09% error rate)  ⚠️ Slightly elevated
RPS:             145.8
p50:             220ms
p95:             580ms                   ⚠️ Above target
p99:             1,200ms                 ⚠️ Needs optimization
Max:             8,500ms
```

**Assessment:** ⚠️ **PASS WITH WARNINGS** — Need optimization at p95+

**Actions:**
1. Add database indexes for slow queries
2. Enable caching for catalog endpoints
3. Increase API server resources (CPU/memory)
4. Review connection pool configuration

---

## Expected Baseline Metrics (Staging)

Based on typical deployment:

### Light Load (20 users, 5 min)

| Metric | Expected | Range |
|--------|----------|-------|
| RPS | 5-10 | 4-12 |
| p50 | 100-150ms | 50-200ms |
| p95 | 250-350ms | 150-500ms |
| p99 | 400-700ms | 200-1000ms |
| Error Rate | 0-1% | 0-2% |

### Normal Load (50 users, 10 min)

| Metric | Expected | Range |
|--------|----------|-------|
| RPS | 15-25 | 12-30 |
| p50 | 150-200ms | 100-250ms |
| p95 | 350-500ms | 250-800ms |
| p99 | 700-1200ms | 500-2000ms |
| Error Rate | 0-1% | 0-2% |

### Heavy Load (100 users, 10 min)

| Metric | Expected | Range |
|--------|----------|-------|
| RPS | 50-100 | 40-120 |
| p50 | 200-300ms | 150-400ms |
| p95 | 500-800ms | 300-1500ms |
| p99 | 1000-2000ms | 700-3000ms |
| Error Rate | 0-2% | 0-3% |

### Spike Load (200 users, 5 min)

| Metric | Expected | Range |
|--------|----------|-------|
| RPS | 100-200 | 80-250 |
| p50 | 300-500ms | 200-800ms |
| p95 | 800-1500ms | 500-2500ms |
| p99 | 2000-4000ms | 1000-6000ms |
| Error Rate | 1-3% | 0-5% |

**Note:** Baselines vary by infrastructure. Use `--baseline` flag to compare against previous runs.

---

## CSV Output Reference

### stats.csv

```csv
Name,# requests,# failures,Median response time,Average response time,...
GET /personas,2400,8,145,180,...
POST /chat/{persona_id},1850,25,520,650,...
GET /analytics/dashboard,350,2,280,315,...
Aggregated,2145,12,180,225,...
```

### response_times.csv

```csv
Name,# 2xx,# 3xx,# 4xx,# 5xx,Total Response Time,Average Response Time,...
GET /personas,2392,0,8,0,432000,180,...
```

### failures.csv

```csv
Method,Name,# failures,Failure,Method,Exception
GET,/personas,8,500 Internal Server Error,...
```

---

## Troubleshooting

### Issue: "Connection refused" (port 8000)

```bash
# Check if API is running
ps aux | grep uvicorn

# Start API server
cd /home/user/persona-platform
python -m uvicorn api.main:app --reload --port 8000

# Or use Docker
docker-compose up -d api
```

### Issue: "Too many open files"

```bash
# Increase file descriptor limit
ulimit -n 65536

# Or add to /etc/security/limits.conf
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Restart your session
```

### Issue: High Error Rate (>5%)

```bash
# Check API logs
docker logs persona-api | grep -i error | tail -20

# Check database connections
psql -U persona -d persona_hub -c "SELECT count(*) FROM pg_stat_activity;"

# Check system resources
top -b -n 1 | head -20

# Reduce load and retry
./run_load_tests.sh light
```

### Issue: p95 Response Time Too High (>1000ms)

```bash
# Identify slow endpoints
python tests/analyze_load_results.py results/ --slow-threshold=500

# Check database query performance
EXPLAIN ANALYZE SELECT ... FROM personas WHERE ...;

# Enable caching for catalog
curl -X POST http://localhost:8000/cache/enable

# Profile slow endpoints
python -m cProfile -s cumulative api/main.py
```

### Issue: WebSocket Connection Failures

```bash
# Test WebSocket connectivity
wscat -c ws://localhost:8000/ws/chat/persona_socrates

# Check WebSocket server logs
docker logs persona-api | grep -i websocket

# Verify proxy configuration (if behind nginx)
curl -I http://localhost:8000/ws/chat/persona_socrates
# Should return 101 Switching Protocols
```

### Issue: Out of Memory

```bash
# Reduce concurrent users
./run_load_tests.sh light  # Start with 20 users

# Monitor memory during test
watch -n 1 'free -h'

# Increase swap (temporary)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Advanced: Distributed Load Testing

For testing 1000+ concurrent users, use Locust distributed mode:

```bash
# Terminal 1: Start master
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --master \
  --master-bind-host=0.0.0.0 \
  --master-bind-port=5557

# Terminal 2, 3, 4, ...: Start workers
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --worker \
  --master-host=localhost \
  --master-port=5557

# Access dashboard at http://localhost:8089
```

### Docker Distributed Setup

```bash
# Start master + 3 workers
docker-compose -f docker-compose.load-test.yml up -d

# Monitor
docker-compose -f docker-compose.load-test.yml logs -f locust-master

# Stop
docker-compose -f docker-compose.load-test.yml down
```

---

## CI/CD Integration

### GitHub Actions Workflow

Load tests run automatically on staging every week:

```bash
# View results
gh workflow view load-test

# Manually trigger
gh workflow run load-test.yml --ref main
```

### Performance Regression Detection

```bash
# Compare against baseline
python tests/analyze_load_results.py \
  --baseline=results/baseline_20260601.json \
  --current=results/test_run.json \
  --threshold=10  # Warn if >10% regression

# Expected output:
# ✅ p95 response time: 285ms (baseline 280ms, +1.8% — OK)
# ⚠️  p99 response time: 950ms (baseline 750ms, +26.7% — REGRESSION)
```

---

## Performance Optimization Guide

If tests show poor results, follow this process:

### 1. Identify Bottleneck

```bash
# Which endpoints are slowest?
python tests/analyze_load_results.py results/ --by-endpoint

# Sample output:
# POST /chat/{persona_id}:      p95=850ms, 78 failures
# GET /analytics/dashboard:     p95=520ms,  2 failures
# GET /personas:                p95=285ms,  0 failures
```

### 2. Database Optimization

```bash
# Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

# Add missing indexes
CREATE INDEX idx_personas_created ON personas(created_at DESC);
CREATE INDEX idx_chats_user_id ON chats(user_id);

# Analyze table
ANALYZE personas;
```

### 3. Caching Strategy

```python
# Enable Redis caching
export REDIS_URL=redis://localhost:6379

# Cache catalog (24 hours)
@cache(ttl=86400)
def get_personas(offset, limit):
    ...

# Cache analytics (1 hour)
@cache(ttl=3600)
def get_dashboard_summary():
    ...
```

### 4. Connection Pool Tuning

```python
# api/db.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Increase from default 5
    max_overflow=40,        # Allow overflow connections
    pool_pre_ping=True,     # Test before use
    pool_recycle=3600,      # Recycle after 1 hour
)
```

### 5. Scale Infrastructure

```bash
# Increase API server resources
docker-compose.yml:
  api:
    deploy:
      resources:
        limits:
          cpus: "4"         # Increase from 2
          memory: 2G        # Increase from 1G

# Add load balancer for multiple API instances
# (See docker-compose.yml for nginx configuration)
```

---

## Monitoring During Load Test

### Real-time Dashboard

```bash
# Option 1: Locust Web UI (automatic)
# Opens at http://localhost:8089 during test

# Option 2: Terminal monitoring
watch -n 1 'curl -s http://localhost:8000/health | jq'
watch -n 1 'docker stats'
watch -n 1 'netstat -an | grep ESTABLISHED | wc -l'
```

### Prometheus Metrics

If Prometheus is enabled:

```bash
# View metrics
curl http://localhost:9090/api/v1/query?query=http_requests_total

# Check API performance
curl 'http://localhost:9090/api/v1/query?query=http_request_duration_seconds_p95'
```

---

## Best Practices

1. **Run tests regularly** — Weekly on staging, monthly on production
2. **Establish baselines** — Document performance for each release
3. **Test realistically** — Match production user behavior and traffic patterns
4. **Monitor continuously** — Use Prometheus/Grafana for real-time insights
5. **Alert on regressions** — 10%+ increase in p95 should trigger investigation
6. **Document results** — Keep historical data for trend analysis
7. **Load test before deployment** — Part of release checklist
8. **Test failover scenarios** — Database failure, service degradation
9. **Optimize gradually** — Address highest-impact issues first
10. **Communicate limits** — Share findings with product/infrastructure teams

---

## Related Documentation

- [CLAUDE.md](./CLAUDE.md) — Persona platform architecture
- [API.md](./api/README.md) — API endpoint reference
- [PERFORMANCE.md](./docs/PERFORMANCE.md) — Performance tuning guide
- [Locust Docs](https://docs.locust.io/) — Official Locust documentation

---

## Support

For load testing issues:

```bash
# Check Locust version
locust --version

# Run with debug output
locust -f tests/load_test_platform.py \
  --host=http://localhost:8000 \
  --loglevel=DEBUG

# Get help
locust --help

# Report issues
# → Create issue with:
#   - Load test scenario (light/normal/heavy/spike)
#   - Results (stats.csv, failures.csv)
#   - System info (OS, Python version, Locust version)
```

---

**Last updated:** 2026-06-11  
**Load testing infrastructure version:** 1.0

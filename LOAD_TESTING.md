# Load Testing Guide (H86)

## Overview

Comprehensive load testing for the payment/billing system (B13-B24) to verify performance, reliability, and idempotency under concurrent load.

**Goals:**
- ✅ Verify payment endpoints handle 50-100+ concurrent users
- ✅ Test webhook idempotency under duplicate/concurrent events
- ✅ Measure latency and throughput
- ✅ Identify database/connection pool bottlenecks
- ✅ Verify multi-currency pricing under load
- ✅ Test wallet contention scenarios

## Load Testing Tools

### 1. Locust (Python-based)
**Best for:** User behavior simulation, realistic workflows

```bash
# Install
pip install locust

# Run basic load test (50 users over 5 minutes)
locust -f tests/load_test_payments.py --host=http://localhost:8000

# Run with specific user count and duration
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m

# Generate HTML report
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 50 \
  --run-time 5m \
  --csv=report
```

### 2. K6 (JavaScript-based)
**Best for:** API-focused testing, precise metrics

```bash
# Install (on Linux)
sudo apt-get install -y apt-transport-https
curl https://dl.k6.io/gpg.key | sudo apt-key add -
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6-stable.list
sudo apt-get update
sudo apt-get install k6

# Run webhook load test
k6 run tests/load_test_webhooks.js

# Run with custom options
k6 run --vus 50 --duration 5m tests/load_test_webhooks.js

# Generate JSON results
k6 run --out json=results.json tests/load_test_webhooks.js
```

## Test Scenarios

### Scenario 1: Light Load (Baseline)
**Users:** 10-20  
**Duration:** 5 minutes  
**Purpose:** Establish baseline metrics

```bash
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 20 \
  --spawn-rate 2 \
  --run-time 5m
```

**Expected Results:**
- Response time p50: < 200ms
- Response time p95: < 500ms
- Error rate: < 1%
- Throughput: 50-100 req/sec

### Scenario 2: Normal Load
**Users:** 50  
**Duration:** 10 minutes  
**Purpose:** Typical production usage

```bash
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 10m
```

**Expected Results:**
- Response time p50: < 300ms
- Response time p95: < 800ms
- Response time p99: < 2s
- Error rate: < 2%
- Throughput: 200-300 req/sec

### Scenario 3: Heavy Load
**Users:** 100  
**Duration:** 10 minutes  
**Purpose:** Stress testing

```bash
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m
```

**Expected Results:**
- Response time p50: < 500ms
- Response time p95: < 2s
- Response time p99: < 5s
- Error rate: < 5%
- Throughput: 400-500 req/sec

### Scenario 4: Spike Load
**Users:** 200 (rapid ramp)  
**Duration:** 5 minutes  
**Purpose:** Burst traffic handling

```bash
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 200 \
  --spawn-rate 50 \
  --run-time 5m
```

**Expected Results:**
- System should handle initial spike
- Response time p99: < 10s
- Error rate: < 10%
- Recovery to normal after spike ends

### Scenario 5: Webhook Idempotency Under Load
**Purpose:** Verify B19 (webhook idempotency) with concurrent events

```bash
k6 run --vus 50 --duration 5m tests/load_test_webhooks.js
```

**Expected Results:**
- All events processed
- Duplicates correctly ignored
- No data corruption
- Throughput: 500-1000 events/sec

## Task Distribution in `load_test_payments.py`

| Task | Weight | Percentage |
|------|--------|-----------|
| Get referral code | 2 | 20% |
| Get wallet balance | 1 | 10% |
| Get invoices | 1 | 10% |
| Checkout persona (USD/EUR/TRY) | 5 | 30% |
| Checkout bundle (USD/EUR) | 3 | 15% |
| Checkout subscription (monthly/annual) | 2 | 10% |
| Checkout with promo | 1 | 5% |
| Checkout with referral | 1 | 5% |
| Billing portal | 1 | 5% |

**Total Weight:** 17 tasks

## Key Metrics to Monitor

### Response Time Metrics
- **Median (p50):** 50% of requests complete in this time
- **p95:** 95% of requests complete in this time
- **p99:** 99% of requests complete in this time
- **Max:** Slowest single request

### Throughput Metrics
- **RPS (Requests Per Second):** Total throughput
- **Total Requests:** Cumulative request count
- **Request Rate by Endpoint:** Breakdown by route

### Error Metrics
- **Error Rate:** Percentage of failed requests
- **Failed Requests:** Count of errors
- **Status Codes:** Distribution (200, 400, 500, etc.)

### System Metrics
- **CPU Usage:** Monitor server CPU during test
- **Memory Usage:** Monitor server memory
- **Database Connections:** Connection pool utilization
- **Disk I/O:** Write operations to SQLite/Postgres

## Running Full Load Test Suite

```bash
#!/bin/bash
# Run complete load test suite (30 minutes total)

echo "🚀 Starting Payment Load Test Suite"
echo "Target: http://localhost:8000"

# 1. Light load baseline (5 min)
echo "📊 Running LIGHT LOAD test (10-20 users)..."
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 20 \
  --spawn-rate 2 \
  --run-time 5m \
  --csv=results/light_load

sleep 30

# 2. Normal load (10 min)
echo "📊 Running NORMAL LOAD test (50 users)..."
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 10m \
  --csv=results/normal_load

sleep 30

# 3. Heavy load (10 min)
echo "📊 Running HEAVY LOAD test (100 users)..."
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --csv=results/heavy_load

sleep 30

# 4. Spike load (5 min)
echo "📊 Running SPIKE LOAD test (200 users)..."
locust -f tests/load_test_payments.py \
  --host=http://localhost:8000 \
  --users 200 \
  --spawn-rate 50 \
  --run-time 5m \
  --csv=results/spike_load

echo "✅ Load test suite complete!"
echo "Results saved to results/ directory"
```

## Performance Tuning Recommendations

### If Response Times Are Slow (p95 > 1s):

1. **Database Indexing**
   ```sql
   -- Add missing indexes
   CREATE INDEX idx_user_api_key_hash ON users(api_key_hash);
   CREATE INDEX idx_purchase_user_persona ON purchases(user_id, persona_id);
   CREATE INDEX idx_invoice_user_status ON invoices(user_id, status);
   ```

2. **Connection Pooling**
   ```python
   # Increase pool size in api/db.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,      # Was 5
       max_overflow=10,   # Was 0
   )
   ```

3. **Query Optimization**
   - Add EXPLAIN ANALYZE to slow queries
   - Consider materialized views for invoice lists
   - Cache referral codes in Redis

### If Error Rate Is High (> 5%):

1. **Increase Timeouts**
   ```python
   # Adjust in api/main.py
   app.add_middleware(TimeoutMiddleware, timeout=30)
   ```

2. **Rate Limit Tuning**
   ```python
   # Increase limits in api/middleware/rate_limiter.py
   ENDPOINT_QUOTAS["/checkout"] = 50  # Was 20
   ```

3. **Database Scaling**
   - Move to Postgres (better concurrency than SQLite)
   - Enable connection pooling
   - Consider read replicas

### If Database Connections Are Exhausted:

1. **Connection Pool Tuning**
   ```python
   pool_size=30,        # More connections
   max_overflow=20,
   pool_recycle=3600,   # Recycle every hour
   ```

2. **Connection Monitoring**
   ```python
   # Monitor active connections
   SELECT count(*) FROM pg_stat_activity;
   ```

## Load Test Results Template

| Metric | Light | Normal | Heavy | Spike |
|--------|-------|--------|-------|-------|
| **Users** | 20 | 50 | 100 | 200 |
| **Duration** | 5m | 10m | 10m | 5m |
| **RPS** | __ | __ | __ | __ |
| **p50 (ms)** | __ | __ | __ | __ |
| **p95 (ms)** | __ | __ | __ | __ |
| **p99 (ms)** | __ | __ | __ | __ |
| **Max (ms)** | __ | __ | __ | __ |
| **Error Rate** | __ | __ | __ | __ |
| **Total Requests** | __ | __ | __ | __ |

## Continuous Load Testing

For production deployments, consider:

1. **Scheduled Tests**
   - Run nightly load tests via CI/CD
   - Compare results to baseline
   - Alert on regressions

2. **Synthetic Monitoring**
   - Use Locust with reporting to monitoring service
   - Track trends over time
   - Identify degradation early

3. **Chaos Engineering**
   - Simulate database latency
   - Kill random connections
   - Test graceful degradation

## Resources

- [Locust Docs](https://docs.locust.io/)
- [K6 Docs](https://k6.io/docs/)
- [Performance Testing Best Practices](https://www.postgresql.org/docs/current/performance-tips.html)
- [Database Indexing Guide](https://use-the-index-luke.com/)

## Next Steps (H87-H89)

- Integrate load tests into CI/CD pipeline
- Set up automated reporting
- Create performance baseline alerts
- Document system capacity limits

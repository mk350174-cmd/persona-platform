# Observability & Monitoring — H95

**Purpose:** Distributed tracing, metrics aggregation, structured logging, and APM instrumentation.

**Integrations:**
- **Jaeger/OpenTelemetry:** Distributed tracing (W3C Trace Context)
- **Prometheus:** Metrics aggregation and alerting
- **Structured logging:** JSON logs with trace context
- **Grafana:** Visualization dashboards

---

## Architecture

### Components

1. **Distributed Tracing (Jaeger)**
   - Traces: unique `trace_id` identifying a request flow across services
   - Spans: individual operations with `span_id`, operation name, duration, status
   - W3C Trace Context: standard HTTP headers for propagation

2. **Metrics (Prometheus)**
   - Types: counter (monotonic), gauge (up/down), histogram (distribution), summary (percentiles)
   - Collection: in-process MetricsCollector aggregates all metrics
   - Export: `/observability/prometheus/metrics` endpoint for scraping

3. **Logging (Structured)**
   - JSON format with timestamp, level, message, context fields
   - Trace context inclusion: trace_id, span_id for correlation
   - Structured fields enable filtering/grouping in log aggregation

4. **APM (Application Performance Monitoring)**
   - RequestMetrics: per-endpoint latency, success rate, error count
   - Baseline tracking: p50/p95/p99 percentiles
   - Regression detection: automatic alerting on degradation

---

## Setup Guide

### 1. Jaeger Deployment

#### Local Development (Docker)

```bash
# Start Jaeger all-in-one container
docker run -d \
  --name jaeger \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# Access UI at http://localhost:16686
```

#### Production (Kubernetes)

```yaml
# values.yaml for Helm chart (jaeger-all-in-one)
jaeger:
  storage:
    type: elasticsearch
    es:
      host: elasticsearch.observability
      port: 9200
  collector:
    enabled: true
    port: 14268
  ui:
    enabled: true
  sampling:
    type: probabilistic
    param: 0.1  # Sample 10% of traces
```

Deploy:
```bash
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm install jaeger jaegertracing/jaeger \
  -n observability \
  -f values.yaml
```

### 2. Prometheus Setup

#### Configuration (prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'persona-platform'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/observability/prometheus/metrics'
    scrape_interval: 10s
```

#### Docker Compose

```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
```

Start:
```bash
docker-compose up -d prometheus
# Access at http://localhost:9090
```

### 3. Grafana Dashboards

#### Installation

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana:latest
```

#### Add Prometheus Data Source

1. Open http://localhost:3000 (admin/admin)
2. Settings → Data Sources → Add Prometheus
3. URL: http://prometheus:9090

#### Import Dashboard

Sample dashboard JSON:

```json
{
  "dashboard": {
    "title": "Persona Platform",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_failed[5m]) / rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Latency p95",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_ms)"
          }
        ]
      }
    ]
  }
}
```

---

## API Reference

### Metrics Endpoints

#### GET /observability/metrics

Get current metrics in JSON format.

**Authentication:** X-API-Key required

**Response:**
```json
{
  "timestamp": "2024-06-10T17:30:00Z",
  "metrics": [
    "http_requests_total 42",
    "http_requests_success 40",
    "http_requests_failed 2"
  ],
  "total_metrics": 3
}
```

#### POST /observability/metrics/record

Record a custom metric.

**Request:**
```json
{
  "name": "persona_compilations",
  "metric_type": "counter",
  "value": 1,
  "labels": {"tier": "pro"}
}
```

**Response:**
```json
{
  "status": "recorded",
  "name": "persona_compilations",
  "type": "counter",
  "value": 1
}
```

#### GET /observability/metrics/summary

Get high-level metrics summary.

**Response:**
```json
{
  "timestamp": "2024-06-10T17:30:00Z",
  "total_requests": 1523,
  "successful_requests": 1450,
  "failed_requests": 73,
  "average_duration_ms": 45.3,
  "success_rate": 95.2
}
```

#### GET /observability/prometheus/metrics

Export metrics in Prometheus text format (for scraping).

**Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total 1523
# HELP http_request_duration_ms HTTP request duration in milliseconds
# TYPE http_request_duration_ms gauge
http_request_duration_ms 45.3
...
```

### Tracing Endpoints

#### POST /observability/traces/record

Record a distributed trace span.

**Request:**
```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "operation": "compile_persona",
  "duration_ms": 250,
  "status": "OK",
  "tags": {
    "persona_id": "machiavelli",
    "tier": "pro"
  }
}
```

**Response:**
```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "operation": "compile_persona",
  "duration_ms": 250,
  "status": "OK",
  "recorded_at": "2024-06-10T17:30:00Z"
}
```

#### GET /observability/traces/{trace_id}

Get trace details by ID.

**Note:** In production, this queries the Jaeger backend. See Jaeger setup above.

**Response:**
```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "status": "trace_retrieval_not_implemented",
  "message": "In production, traces are stored in Jaeger..."
}
```

### Health Checks

#### GET /observability/health/liveness

Pod is running.

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2024-06-10T17:30:00Z"
}
```

#### GET /observability/health/readiness

Pod is ready to receive traffic.

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2024-06-10T17:30:00Z"
}
```

#### GET /observability/health/deep

Deep health check (database, metrics, requests).

**Response:**
```json
{
  "timestamp": "2024-06-10T17:30:00Z",
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy"},
    "metrics": {"status": "healthy", "metric_count": 15},
    "request_metrics": {"status": "healthy", "total_requests": 1523}
  }
}
```

### Logging Endpoints

#### POST /observability/logs/collect

Collect structured logs from clients.

**Request:**
```json
{
  "level": "ERROR",
  "message": "Failed to compile persona",
  "context": {
    "persona_id": "machiavelli",
    "error_code": "TIMEOUT"
  }
}
```

**Response:**
```json
{
  "status": "logged",
  "level": "ERROR",
  "message": "Failed to compile persona",
  "timestamp": "2024-06-10T17:30:00Z"
}
```

---

## Integration Guide

### 1. Distributed Tracing in API Handlers

```python
from api.observability import TraceContext, trace_span
from api.auth import get_current_user

@app.post("/v1/compile/{persona_id}")
def compile_persona(
    persona_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    # Extract or create trace context from request headers
    trace_context = TraceContext.from_headers(dict(request.headers))
    
    with trace_span("compile_persona", trace_context, tags={
        "persona_id": persona_id,
        "user_id": user.id,
    }) as span:
        # Your compilation logic
        result = compile_persona_impl(persona_id)
        span.add_tag("status", "success")
        return result
```

### 2. Custom Metrics

```python
from api.observability import get_metrics_collector

collector = get_metrics_collector()

# Record counter (compilation attempts)
collector.record_counter(
    "persona_compilations",
    labels={"tier": user.tier, "persona": persona_id}
)

# Record gauge (current active users)
collector.record_gauge("active_users", active_count)

# Record histogram (compilation latency)
collector.record_histogram(
    "compilation_latency_ms",
    duration_ms,
    labels={"tier": user.tier}
)
```

### 3. Structured Logging

```python
from api.observability import get_structured_logger

logger = get_structured_logger("persona_compiler")

logger.info(
    "Compilation started",
    persona_id=persona_id,
    user_id=user.id,
    tier=user.tier,
    trace_id=trace_context.trace_id,
)

logger.error(
    "Compilation failed",
    persona_id=persona_id,
    error=str(exception),
    trace_id=trace_context.trace_id,
)
```

### 4. APM Instrumentation

```python
from api.observability import get_request_metrics

@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    
    metrics = get_request_metrics()
    metrics.record_request(duration_ms, response.status_code)
    
    return response
```

---

## W3C Trace Context Standard

Trace context is propagated via HTTP headers:

```
traceparent: 00-{trace_id}-{span_id}-01
baggage: user_id=12345,tier=pro
```

### Components

- **Version (00):** W3C version 0
- **trace_id (32 hex):** Unique trace identifier (e.g., 4bf92f3577b34da6a3ce929d0e0e4736)
- **span_id (16 hex):** Current span (e.g., 00f067aa0ba902b7)
- **flags (01):** Bit 0 = sampled (1 = yes, 0 = no)
- **baggage:** Key-value pairs (user_id, session_id, etc.)

### Example Flow

1. Client → API: `GET /v1/compile/socrates`
   - No traceparent header
   - Server generates: trace_id=abc123..., span_id=def456...
   - Response includes: `traceparent: 00-abc123...-def456...-01`

2. Client receives response, stores traceparent
3. Client → API: `POST /v1/compile/socrates`
   - Includes: `traceparent: 00-abc123...-xyz789...-01`
   - Server uses same trace_id, creates new span_id
   - Jaeger correlates both requests

---

## Alerting Rules

### Prometheus Alert Rules (prometheus-rules.yml)

```yaml
groups:
  - name: persona-platform
    rules:
      - alert: HighErrorRate
        expr: |
          (rate(http_requests_failed[5m]) / rate(http_requests_total[5m])) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected ({{ $value | humanizePercentage }})"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, http_request_duration_ms) > 1000
        for: 10m
        annotations:
          summary: "High p95 latency ({{ $value }}ms)"

      - alert: FailedRollback
        expr: |
          rate(rollback_failures[5m]) > 0
        for: 1m
        annotations:
          summary: "Rollback failure detected"
```

---

## Troubleshooting

### Missing Metrics

**Issue:** No metrics appearing in Prometheus

**Solution:**
1. Verify endpoint is registered: `curl http://localhost:8000/observability/prometheus/metrics`
2. Check Prometheus scrape config points to correct URL
3. Verify authentication (if X-API-Key required, add to scrape config)
4. Check logs for errors: `docker logs prometheus`

### High Memory Usage

**Issue:** Metrics collector consuming too much memory

**Solution:**
1. Reduce metric retention: `prometheus --storage.tsdb.retention.time=7d`
2. Disable high-cardinality metrics
3. Implement metric downsampling

### Missing Traces in Jaeger

**Issue:** Traces not appearing in Jaeger UI

**Solution:**
1. Verify Jaeger endpoint reachable: `curl http://localhost:14268`
2. Check sampling rate: ensure not filtering all traces
3. Verify span export is implemented (currently a no-op in code)
4. Check Jaeger storage backend (Elasticsearch, etc.)

---

## Performance Considerations

### Metrics Collection

- **In-memory storage:** Current implementation stores metrics in Python dict (single-threaded)
- **Scale to distributed:** Use Redis or Prometheus remote write for multi-instance
- **Cardinality:** Each unique label combination is a separate metric — limit to <10k combinations

### Trace Sampling

Default: 100% sampling (all traces sent to Jaeger)

**Adjust sampling rate:**
```python
@app.middleware("http")
async def sample_traces(request: Request, call_next):
    # Sample 10% of requests
    should_sample = random.random() < 0.1
    request.state.sampled = should_sample
    return await call_next(request)
```

### Log Volume

Default: JSON logs with full context (40-60 bytes/log)

**At 1000 req/s with 10 logs/req:**
- 10,000 logs/sec × 50 bytes = 500 KB/sec = 43 GB/day

**Mitigations:**
1. Reduce log level in production (INFO only, not DEBUG)
2. Use structured fields (small keys)
3. Filter logs at aggregation layer

---

## Examples

### Example 1: Trace Full Compilation Flow

```python
# Client sets traceparent header
headers = {
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
}

# API handler
@app.post("/v1/compile/{persona_id}")
def compile_persona(persona_id: str, request: Request):
    trace_context = TraceContext.from_headers(dict(request.headers))
    
    with trace_span("compile_persona", trace_context) as span:
        # Compilation steps
        with trace_span("load_persona", trace_context) as load_span:
            persona = load_from_catalog(persona_id)
        
        with trace_span("generate_code", trace_context) as gen_span:
            code = generate_persona_code(persona)
        
        with trace_span("validate", trace_context) as val_span:
            validate_code(code)
    
    # Spans are: load_persona → generate_code → validate → compile_persona
    # All linked by same trace_id in Jaeger
```

### Example 2: Monitor Compilation by Tier

```python
# After each compilation, record metrics
tier = user.subscription_tier
collector.record_histogram(
    "compilation_time_ms",
    duration_ms,
    labels={"tier": tier}
)

# In Prometheus:
# histogram_quantile(0.95, compilation_time_ms{tier="pro"})
# Shows p95 latency for pro tier users only
```

### Example 3: Alert on Rollback Frequency

```yaml
# Alert if more than 3 rollbacks in 1 hour
- alert: FrequentRollbacks
  expr: |
    rate(rollback_total[1h]) > 3
  for: 5m
  annotations:
    summary: "{{ $value }} rollbacks in last hour"
```

---

## Next Steps

1. **Deploy Jaeger:** Set up local container or cloud instance
2. **Configure Prometheus:** Point scraper to `/observability/prometheus/metrics`
3. **Build Grafana dashboards:** Visualize request rate, latency, error rate
4. **Integrate tracing:** Add `trace_span` context managers to API handlers
5. **Monitor in production:** Use liveness/readiness probes for Kubernetes
6. **Archive traces:** Configure Elasticsearch backend for long-term trace retention

---

## References

- **W3C Trace Context:** https://w3c.github.io/trace-context/
- **Jaeger:** https://www.jaegertracing.io/
- **Prometheus:** https://prometheus.io/
- **Grafana:** https://grafana.com/
- **OpenTelemetry:** https://opentelemetry.io/

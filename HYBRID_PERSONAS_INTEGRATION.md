# Hybrid Personas Integration Guide — Phase 7 Production

**Version:** 1.0  
**Status:** Production Ready  
**Date:** June 15, 2026  
**Audience:** Platform engineers, product managers, frontend developers

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [K-Layer Mapping Reference](#k-layer-mapping-reference)
5. [Pricing & Purchasing](#pricing--purchasing)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Integration Checklist](#integration-checklist)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

### What are Hybrid Personas?

Hybrid Personas are expert-engineered persona combinations that blend multiple K-layer psychological dimensions to represent real-world user archetypes. Each hybrid persona is defined by:

- **Active K-Layers**: Dominant psychological traits (weight: 0.85)
- **Suppressed K-Layers**: Muted traits (weight: 0.15)
- **Neutral K-Layers**: Unmapped traits (weight: 0.5)

### Key Numbers

| Attribute | Value |
|-----------|-------|
| **Total Personas** | 48 hybrid combinations |
| **K-Layer Dimensions** | 98 active (K2-K99) |
| **Price per Persona** | 14.99 USD |
| **Matching Algorithm** | Cosine similarity with LRU caching |
| **Cache Size** | 1024 vectors |
| **Matching Latency Target** | < 500ms |

### Use Cases

1. **Psychographic Segmentation**: Identify user archetypes from quiz responses
2. **Persona-Driven Recommendations**: Suggest products/content matching user type
3. **Behavioral Targeting**: Tailor features based on persona characteristics
4. **User Research**: Validate persona distributions in cohorts

---

## Architecture

### Data Flow

```
Quiz Submission (50 HPEP-100 answers)
         ↓
extract_persona() → K-layer vector (100 elements)
         ↓
match_user_to_personas() → Cosine similarity (48 comparisons)
         ↓
LRU Cache Hit/Miss → Record to DB
         ↓
PersonaMatch audit record
         ↓
Return: top_persona_id, top_5_ids, top_5_scores
         ↓
React Component → Display Results → Checkout
```

### Database Schema

#### `hybrid_personas` Table

```sql
CREATE TABLE hybrid_personas (
  id VARCHAR(36) PRIMARY KEY,
  persona_id VARCHAR(64) UNIQUE NOT NULL,           -- e.g., "hybrid_001"
  combination_number INTEGER UNIQUE NOT NULL,       -- 1-48
  name_tr VARCHAR(255) NOT NULL,                    -- Turkish name
  name_en VARCHAR(255) NOT NULL,                    -- English name
  active_k_layers JSON NOT NULL,                    -- [1, 5, 8, 12, ...]
  suppressed_k_layers JSON NOT NULL,                -- [3, 7, 15, ...]
  use_case VARCHAR(1000) NOT NULL,
  characteristic VARCHAR(2000) NOT NULL,
  example_outputs VARCHAR(2000),
  price_usd INTEGER DEFAULT 1499,                   -- Cents (14.99 USD)
  is_available BOOLEAN DEFAULT true,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

-- Performance indices
CREATE INDEX ix_hybrid_personas_available ON hybrid_personas(is_available);
CREATE INDEX ix_hybrid_personas_persona_id ON hybrid_personas(persona_id);
CREATE UNIQUE INDEX ix_hybrid_personas_number ON hybrid_personas(combination_number);
```

#### `persona_matches` Table (Audit)

```sql
CREATE TABLE persona_matches (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  submission_id VARCHAR(36) NOT NULL,
  top_persona_id VARCHAR(64) NOT NULL,
  is_historical BOOLEAN DEFAULT false,              -- Fallback match?
  match_score INTEGER,                               -- 0-100 percentile
  top_5_persona_ids JSON NOT NULL,                  -- ["hybrid_001", ...]
  top_5_scores JSON NOT NULL,                       -- [92, 85, 78, 71, 65]
  created_at DATETIME NOT NULL,
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (submission_id) REFERENCES quiz_submissions(id),
  FOREIGN KEY (top_persona_id) REFERENCES hybrid_personas(persona_id)
);

-- Audit indices
CREATE INDEX ix_persona_matches_user_created ON persona_matches(user_id, created_at);
CREATE INDEX ix_persona_matches_submission_id ON persona_matches(submission_id);
CREATE INDEX ix_persona_matches_top_persona ON persona_matches(top_persona_id);
```

#### `quiz_submissions` Extensions

```sql
ALTER TABLE quiz_submissions ADD COLUMN matched_hybrid_persona_id VARCHAR(64);
ALTER TABLE quiz_submissions ADD COLUMN hybrid_match_score INTEGER;
ALTER TABLE quiz_submissions ADD COLUMN top_5_hybrid_matches JSON;
ALTER TABLE quiz_submissions ADD COLUMN top_5_hybrid_scores JSON;
ALTER TABLE quiz_submissions ADD FOREIGN KEY (matched_hybrid_persona_id) 
  REFERENCES hybrid_personas(persona_id);
```

---

## API Endpoints

### 1. Get All Hybrid Personas

```http
GET /api/v1/personas/hybrid
X-API-Key: sk_test_...

Response (200 OK):
{
  "count": 48,
  "personas": [
    {
      "persona_id": "hybrid_001",
      "combination_number": 1,
      "name_tr": "Yapıcı Lider",
      "name_en": "Creative Leader",
      "use_case": "Tech leaders, product managers",
      "characteristic": "High innovation, low risk-aversion",
      "price_usd": 1499,
      "is_available": true
    },
    ...
  ]
}
```

**Rate Limit:** 100 req/min per API key  
**Cache:** 5 minutes (public data)

---

### 2. Get Single Hybrid Persona Details

```http
GET /api/v1/personas/hybrid/{persona_id}
X-API-Key: sk_test_...

Example:
GET /api/v1/personas/hybrid/hybrid_001

Response (200 OK):
{
  "persona_id": "hybrid_001",
  "combination_number": 1,
  "name_tr": "Yapıcı Lider",
  "name_en": "Creative Leader",
  "active_k_layers": [1, 5, 8, 12, 14, 18, 22, 27, 31, 35],
  "suppressed_k_layers": [3, 7, 15, 19, 24, 30],
  "use_case": "Tech leaders, product managers specializing in innovation",
  "characteristic": "Highly creative, ambitious, risk-tolerant, detail-oriented",
  "example_outputs": "User would design novel solutions, lead change initiatives",
  "price_usd": 1499,
  "is_available": true,
  "created_at": "2026-06-15T10:00:00Z",
  "updated_at": "2026-06-15T10:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Persona ID doesn't exist
- `403 Forbidden`: User doesn't have access (not purchased)

---

### 3. Match User K-Layer to Personas

```http
POST /api/v1/personas/match
X-API-Key: sk_test_...
Content-Type: application/json

Request Body:
{
  "user_k_layer": [0.5, 0.6, 0.7, ..., 0.4],  // 100 elements (0-1)
  "top_k": 5                                   // Optional, default 5
}

Response (200 OK):
{
  "top_persona_id": "hybrid_001",
  "top_5_ids": ["hybrid_001", "hybrid_005", "hybrid_012", "hybrid_003", "hybrid_008"],
  "top_5_scores": [92, 85, 78, 71, 65],       // 0-100 percentile
  "profile": {
    "user_vector_stats": {
      "mean": 0.52,
      "std": 0.18,
      "min": 0.15,
      "max": 0.95
    },
    "is_historical": false,
    "total_personas_compared": 48,
    "top_k": 5,
    "top_persona_details": {
      "persona_id": "hybrid_001",
      "name_tr": "Yapıcı Lider",
      "name_en": "Creative Leader",
      "match_score": 92,
      "use_case": "Tech leaders, product managers",
      "characteristic": "High innovation, low risk-aversion",
      "combination_number": 1
    },
    "latency_ms": 247.5,
    "cache_stats": {
      "size": 12,
      "maxsize": 1024,
      "utilization": 0.0117,
      "hits": 1245,
      "misses": 89,
      "hit_rate": 0.933
    }
  }
}
```

**Validation:**
- `user_k_layer` must be 100 elements (K-layer 0-99)
- Each element must be 0-1 (float)
- `top_k` must be 1-48 (default 5)

**Errors:**
- `400 Bad Request`: Invalid input format
- `503 Service Unavailable`: No personas available (fallback to historical)

**Latency SLA:** < 500ms (p95: < 600ms)

---

### 4. Search Hybrid Personas (by characteristic)

```http
GET /api/v1/personas/search/hybrid?q=creative&limit=10
X-API-Key: sk_test_...

Response (200 OK):
{
  "query": "creative",
  "count": 5,
  "results": [
    {
      "persona_id": "hybrid_001",
      "name_en": "Creative Leader",
      "match_score": 0.95
    },
    ...
  ]
}
```

**Query Fields:** name_tr, name_en, characteristic, use_case

---

### 5. Get User's Persona Match History

```http
GET /api/v1/users/me/persona-matches?limit=10&offset=0
X-API-Key: sk_test_...

Response (200 OK):
{
  "count": 3,
  "matches": [
    {
      "id": "match_001",
      "submission_id": "sub_001",
      "top_persona_id": "hybrid_001",
      "match_score": 92,
      "top_5_ids": ["hybrid_001", "hybrid_005", ...],
      "top_5_scores": [92, 85, 78, 71, 65],
      "is_historical": false,
      "created_at": "2026-06-15T12:00:00Z"
    },
    ...
  ]
}
```

---

## K-Layer Mapping Reference

### Active K-Layers by Persona Type

| Layer Index | Layer Name | Meaning |
|-------------|-----------|---------|
| K1 | Risk Tolerance | High = risk-seeking; Low = risk-averse |
| K2 | Creativity | Divergent thinking, novelty-seeking |
| K3 | Analytical Depth | Detail-orientation, complexity preference |
| K4 | Social Orientation | People-focused vs task-focused |
| K5 | Emotional Intensity | Range of emotional expression |
| K6 | Stability | Consistency, predictability preference |
| K7 | Ambition | Goal-directedness, achievement drive |
| K8 | Collaboration | Teamwork vs independence |
| ... | ... | (continues to K98) |

### Example Persona Mapping

**Hybrid Persona 001: "Yapıcı Lider" (Creative Leader)**

```json
{
  "persona_id": "hybrid_001",
  "active_k_layers": [
    2,   // High Creativity
    7,   // High Ambition
    8,   // Collaboration
    12,  // Visionary thinking
    18,  // Change leadership
    22,  // Strategic planning
    31,  // Cross-cultural awareness
    35   // Adaptive learning
  ],
  "suppressed_k_layers": [
    3,   // Low detail-orientation (big picture)
    15,  // Low risk-aversion
    19,  // Low risk-aversion
    24,  // Low process-orientation
    30   // Low routine preference
  ]
}
```

### Finding Personas by K-Layer

To find all personas where K-layer 2 (Creativity) is active:

```sql
SELECT persona_id, name_en 
FROM hybrid_personas 
WHERE JSON_CONTAINS(active_k_layers, JSON_ARRAY(2));
```

---

## Pricing & Purchasing

### Pricing Model

| Item | Price | Currency | Notes |
|------|-------|----------|-------|
| Single Hybrid Persona | 14.99 | USD | One-time purchase |
| Persona Bundle (10) | 99.99 | USD | Save 33% |
| Persona Bundle (48) | 299.99 | USD | All personas + updates |
| Monthly Subscription | 19.99 | USD | Unlimited personas + analytics |

### Purchasing Flow

1. **User Submits Quiz** → Receives K-layer vector + top 5 persona matches
2. **User Selects Persona** → Clicks "View Details" or "Purchase"
3. **Checkout Page** → Stripe payment form
4. **Payment Processing** → Webhook confirmation
5. **Grant Access** → User gets persona unlock, analytics access
6. **Download/Compile** → User can download persona file or use API

### Database Grant Logic

```python
# After Stripe webhook confirmation:
user.grant_persona_access(persona_id="hybrid_001")

# Then user can:
# 1. Read persona details via GET /api/v1/personas/hybrid/hybrid_001
# 2. Download persona file
# 3. Access analytics dashboard
# 4. Use persona in compilations
```

---

## Performance Benchmarks

### Target Latencies (Production SLA)

| Operation | Target | p95 | p99 |
|-----------|--------|-----|-----|
| **POST /personas/match** | < 500ms | < 600ms | < 1000ms |
| **GET /personas/hybrid** (list all) | < 200ms | < 250ms | < 300ms |
| **GET /personas/hybrid/{id}** | < 100ms | < 150ms | < 200ms |
| **GET /personas/search/hybrid** | < 300ms | < 400ms | < 500ms |
| **React render (PersonaMatchResults)** | < 1000ms | < 1200ms | < 1500ms |

### Cache Performance

**LRU Cache Configuration:**
- **Max Size:** 1024 K-layer vectors
- **Entry Size:** ~400 bytes (98-dim float32 array)
- **Memory Usage:** ~400 KB max
- **Eviction Policy:** Least recently used

**Hit Rate Targets:**
- With 48 personas: > 70% (typical user reruns quiz)
- In production: > 85% (with repeated users)

### Load Test Results

After importing 48 personas:

```
Concurrent Users: 50
Duration: 60 seconds
Total Requests: 2,500

Results:
  Success Rate: 99.2%
  Mean Latency: 245ms
  P95 Latency: 387ms
  P99 Latency: 521ms
  Throughput: 41.7 req/sec
  
Cache Performance:
  Hit Rate: 93.1%
  Cache Size: 48/1024
```

---

## Integration Checklist

### Backend Integration

- [ ] Database migration 009 applied (`alembic upgrade 009`)
- [ ] 48 personas imported via `scripts/import_hybrid_personas.py`
- [ ] LRU cache configured in `api/persona_matching_service.py`
- [ ] All database indices created and verified
- [ ] Quiz submission updated with matching columns
- [ ] PersonaMatch audit records enabled
- [ ] Error handling for no-personas-available scenario

### API Integration

- [ ] Endpoint `/api/v1/personas/hybrid` working (list)
- [ ] Endpoint `/api/v1/personas/hybrid/{id}` working (detail)
- [ ] Endpoint `/api/v1/personas/match` working (matching)
- [ ] Endpoint `/api/v1/personas/search/hybrid` working (search)
- [ ] All endpoints return correct HTTP status codes
- [ ] Rate limiting configured (100 req/min per key)
- [ ] Error responses follow standard format

### Frontend Integration

- [ ] `PersonaMatchResults.jsx` component created
- [ ] `HybridPersonaDetail.jsx` page implemented
- [ ] `PersonaMatchResults.css` styled
- [ ] Results page displays top 5 personas
- [ ] Persona details page shows K-layer info
- [ ] Checkout button integrated with Stripe
- [ ] Loading states and error handling

### Testing

- [ ] Unit tests passing: `pytest tests/test_hybrid_personas.py`
- [ ] Integration tests passing (quiz → matching)
- [ ] Load tests passing (50+ concurrent)
- [ ] React components render correctly
- [ ] E2E tests passing (browser)

### Monitoring & Logging

- [ ] Logging configured for persona matching
- [ ] Performance metrics collected (latency, cache stats)
- [ ] Error rates tracked (matching failures, timeouts)
- [ ] Database query performance monitored
- [ ] Cache hit rates tracked

### Documentation

- [ ] API documentation updated
- [ ] K-layer mapping documented
- [ ] Deployment guide completed
- [ ] Troubleshooting guide written
- [ ] FAQ section prepared

---

## Troubleshooting

### Issue: No Personas Available

**Symptom:** Matching endpoint returns error `no_personas_available`

**Causes:**
1. Migration 009 not applied
2. `is_available` column not set to true
3. Import script failed

**Solution:**
```bash
# 1. Check migration status
alembic current

# 2. Verify personas in DB
psql -U postgres -d persona_platform -c \
  "SELECT COUNT(*) FROM hybrid_personas WHERE is_available = true;"

# 3. Re-run import if needed
python scripts/import_hybrid_personas.py --clear

# 4. Verify indices
psql -U postgres -d persona_platform -c \
  "SELECT * FROM pg_indexes WHERE tablename = 'hybrid_personas';"
```

---

### Issue: Cache Hit Rate Low (< 50%)

**Symptom:** Matching latency high despite cache enabled

**Causes:**
1. Cache not initialized properly
2. User K-layers constantly different (diverse user base)
3. Cache size too small (unlikely with 48 personas)

**Solution:**
```python
# In persona_matching_service.py:
from api.persona_matching_service import _k_layer_cache

# Check cache stats
print(_k_layer_cache.stats())
# Output: {'size': 48, 'utilization': 0.0469, 'hits': 1000, 'misses': 50, 'hit_rate': 0.952}

# Clear cache if corrupted
_k_layer_cache.clear()
```

---

### Issue: Matching Latency > 500ms

**Symptom:** POST /personas/match takes > 500ms consistently

**Causes:**
1. Database query slow (missing indices)
2. Cache disabled
3. High concurrent load
4. Database connection pool exhausted

**Solution:**
```bash
# 1. Verify indices
psql -U postgres -d persona_platform -c "
  EXPLAIN ANALYZE 
  SELECT * FROM hybrid_personas WHERE is_available = true;"

# 2. Check connection pool
# In api/main.py, verify pool_size and pool_recycle settings

# 3. Monitor active queries
psql -U postgres -d persona_platform -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 4. Check cache hit rate
# From API response: profile.cache_stats.hit_rate
# Should be > 70% for healthy cache
```

---

### Issue: PersonaMatch Records Not Creating

**Symptom:** Quiz submission completes but no PersonaMatch record in DB

**Causes:**
1. Foreign key constraint violation
2. Matching logic not triggered
3. Database transaction rollback

**Solution:**
```python
# In api/quiz_service.py, verify trigger:
def extract_persona(answers_dict, db=None):
    k_layer = ... # extraction
    if db:
        # Should trigger matching
        top_persona_id, top_5_ids, top_5_scores, profile = \
            match_user_to_personas(k_layer, db)
        # Record match
        PersonaMatch.create(...)
```

---

## FAQ

### Q: Can a user have multiple personas?

**A:** Yes. Each quiz submission creates a new `QuizSubmission` and `PersonaMatch` record. We keep a separate `UserPersona` cache with the latest result. Users can track their persona history and see how their profile evolves.

---

### Q: What if a user submits invalid K-layer vector?

**A:** The matching algorithm has graceful degradation:
1. If vector length != 100, pad/truncate to 98 elements
2. If norms are degenerate (< 1e-6), return neutral score 0.5
3. If all matching fails, return error 503 with fallback suggestion

---

### Q: How do I add a new hybrid persona?

**A:** Add a line to `data/hybrid_personas_raw.jsonl`:

```json
{
  "id": "hybrid_049",
  "number": 49,
  "name_tr": "Yeni Persona",
  "name_en": "New Persona",
  "active_layers": [2, 5, 8, 12],
  "suppressed_layers": [3, 15],
  "use_case": "...",
  "characteristic": "..."
}
```

Then re-run import script:
```bash
python scripts/import_hybrid_personas.py
```

---

### Q: How do I deprecate a persona?

**A:** Set `is_available = false` in the database:

```sql
UPDATE hybrid_personas 
SET is_available = false 
WHERE persona_id = 'hybrid_049';
```

This persona won't be returned by API but existing matches remain in the audit log.

---

### Q: What happens if matching fails?

**A:** The system returns:
```json
{
  "top_persona_id": null,
  "top_5_ids": [],
  "top_5_scores": [],
  "profile": {
    "error": "no_personas_available",
    "is_historical": true,
    "message": "No hybrid personas available; using historical neutral baseline"
  }
}
```

The `is_historical` flag indicates this was a fallback. The system logs this incident for monitoring.

---

### Q: How are personas ranked in top-5?

**A:** By cosine similarity score (0-1), converted to percentile (0-100):

```
similarity = (user_vec · persona_vec) / (||user_vec|| * ||persona_vec||)
percentile = round(similarity * 100)
```

Ties are broken by persona_id (alphabetical).

---

### Q: What's the difference between top_5_ids and top_5_scores?

**A:** 
- `top_5_ids`: ["hybrid_001", "hybrid_005", ...] — The persona IDs
- `top_5_scores`: [92, 85, 78, 71, 65] — Match percentiles (0-100)

Indices correspond: `top_5_ids[0]` has score `top_5_scores[0]`.

---

### Q: Can I use the API without authentication?

**A:** The `/api/v1/personas/hybrid` list endpoint is public (no auth required) but rate-limited. Detailed persona data and matching require `X-API-Key` header.

---

### Q: What's the data retention policy?

**A:** 
- `hybrid_personas`: Indefinite (master reference)
- `persona_matches`: 24 months (GDPR compliance)
- `quiz_submissions`: 24 months (audit trail)

After retention period, data is anonymized.

---

## Related Documents

- [HYBRID_PERSONAS_DEPLOYMENT.md](./HYBRID_PERSONAS_DEPLOYMENT.md) — Staging deployment steps
- [API Documentation](./docs/API.md) — Full API reference
- [Architecture Guide](./docs/ARCHITECTURE.md) — System design details
- [Performance Tuning](./docs/PERFORMANCE.md) — Optimization strategies

---

**Document Version:** 1.0  
**Last Updated:** June 15, 2026  
**Maintained By:** Platform Team  
**Questions?** File an issue or contact platform-support@company.com

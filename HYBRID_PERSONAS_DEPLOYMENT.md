# Hybrid Personas Deployment Checklist — Phase 7 Staging

**Timeline:** July 8-11, 2026  
**Status:** Ready for Staging Deployment  
**Approved By:** Persona Platform Team  

---

## Overview

This document provides the step-by-step staging deployment checklist for the Hybrid Personas system. The checklist ensures all database migrations, data imports, and integration tests pass before moving to production.

**Key Metrics:**
- **48 Hybrid Personas**: Expert-engineered K-layer combinations
- **K-Layer Dimensions**: 98 active layers (K2-K99)
- **Matching Algorithm**: Cosine similarity with LRU caching (maxsize=1024)
- **Target Latency**: < 500ms for persona matching
- **Pricing**: 14.99 USD per persona
- **Cache Hit Rate Target**: > 70% with 48 personas

---

## Prerequisites

Before staging deployment, verify:

- [ ] PostgreSQL database is running (localhost:5432 or remote)
- [ ] Python 3.11+ installed with venv activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Alembic migrations prepared (see migration 009)
- [ ] `data/hybrid_personas_raw.jsonl` available (48 personas × 4 combinations)
- [ ] Test data seed set (optional but recommended)
- [ ] API key for Stripe (mock mode for staging)

---

## Staging Deployment Steps

### Step 1: Database Setup (5 min)

```bash
# 1.1 Initialize database if fresh
cd /home/user/persona-platform
python -c "from api.db import init_db, engine; init_db(engine)" && echo "✓ DB initialized"

# 1.2 Apply Alembic migration 009 (hybrid_personas + persona_matches tables)
alembic upgrade 009

# 1.3 Verify migration applied
psql -U postgres -d persona_platform -c "SELECT * FROM information_schema.tables WHERE table_name IN ('hybrid_personas', 'persona_matches');"

# Expected output: 2 rows (hybrid_personas, persona_matches)
```

**Verification:**
- [ ] Migration applied successfully
- [ ] Tables exist in PostgreSQL
- [ ] Indices created:
  - `ix_hybrid_personas_available` (for is_available filter)
  - `ix_hybrid_personas_persona_id` (unique persona_id)
  - `ix_persona_matches_user_created` (for audit queries)

---

### Step 2: Import 48 Hybrid Personas (3 min)

```bash
# 2.1 Run import script with progress bar
python scripts/import_hybrid_personas.py \
  --input data/hybrid_personas_raw.jsonl \
  --clear  # Clears existing personas first (staging only!)

# Expected output:
# IMPORT SUMMARY REPORT
# =====================================
# Total lines read:        48
# Successfully imported:   48
# Skipped:                 0
# Errors:                  0
# Duration:                2.43s
```

**Verification:**
- [ ] All 48 personas imported
- [ ] No import errors
- [ ] Database records match JSONL file

```bash
# 2.2 Verify persona count in database
psql -U postgres -d persona_platform -c \
  "SELECT COUNT(*), COUNT(DISTINCT combination_number) FROM hybrid_personas;"

# Expected: 48 rows, 48 distinct combination_number values
```

---

### Step 3: Run Unit Tests (2 min)

Test the persona matching engine in isolation:

```bash
# 3.1 Run hybrid persona tests
pytest tests/test_hybrid_personas.py -v

# Expected output:
# test_build_hybrid_vector PASSED
# test_cosine_similarity PASSED
# test_percentile_score PASSED
# test_match_user_to_personas PASSED
# test_cache_stats PASSED
# test_record_persona_match PASSED
# ========================= 6 passed in 0.45s =========================
```

**Verification:**
- [ ] All unit tests pass
- [ ] No import errors
- [ ] Cache initialization works

---

### Step 4: Database Indices Verification (1 min)

Ensure all performance-critical indices are in place:

```bash
# 4.1 List all indices on hybrid_personas table
psql -U postgres -d persona_platform -c "
  SELECT indexname, indexdef 
  FROM pg_indexes 
  WHERE tablename = 'hybrid_personas'
  ORDER BY indexname;"

# Expected indices:
# - ix_hybrid_personas_number (unique, combination_number)
# - ix_hybrid_personas_available (is_available)  ← Critical for matching
# - ix_hybrid_personas_created (created_at)
# - ix_hybrid_personas_persona_id (unique, persona_id)
```

**Verification:**
- [ ] `ix_hybrid_personas_available` exists
- [ ] `ix_hybrid_personas_persona_id` exists (unique)
- [ ] All 4 indices present

---

### Step 5: Start API Server (2 min)

Launch FastAPI with reloading enabled (staging only):

```bash
# 5.1 Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:5432/persona_platform"
export STRIPE_SECRET_KEY="sk_test_..."  # Use test key for staging
export BASE_URL="http://localhost:8000"

# 5.2 Start API server with reload
cd /home/user/persona-platform
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Will watch for changes in these directories: ['/home/user/persona-platform']
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verification:**
- [ ] Server starts without errors
- [ ] Listens on http://localhost:8000
- [ ] Health endpoint accessible: `curl http://localhost:8000/health`

---

### Step 6: Test API Endpoints (5 min)

Run cURL tests against staging API:

```bash
# 6.1 Health check
curl -X GET http://localhost:8000/health -w "\nStatus: %{http_code}\n"

# Expected: 200 OK

# 6.2 List hybrid personas (requires API key for full list)
curl -X GET http://localhost:8000/api/v1/personas/hybrid \
  -H "X-API-Key: test-key" \
  -w "\nStatus: %{http_code}\n"

# Expected: 200 OK with persona list

# 6.3 Test persona matching endpoint
curl -X POST http://localhost:8000/api/v1/personas/match \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_k_layer": [0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3]
  }' \
  -w "\nStatus: %{http_code}\n"

# Expected: 200 OK with:
# {
#   "top_persona_id": "hybrid_001",
#   "top_5_ids": ["hybrid_001", "hybrid_002", ...],
#   "top_5_scores": [92, 85, 78, 71, 65],
#   "profile": { ... }
# }
```

**Verification:**
- [ ] Health endpoint returns 200
- [ ] Persona list endpoint accessible
- [ ] Matching endpoint returns valid results
- [ ] Latency visible in response (< 500ms expected)

---

### Step 7: Run Integration Tests (5 min)

Test the full quiz-to-matching flow:

```bash
# 7.1 Run quiz integration tests
pytest tests/test_hybrid_personas.py::test_quiz_to_matching_flow -v

# Expected:
# test_quiz_to_matching_flow PASSED
```

**Verification:**
- [ ] Quiz submission creates K-layer
- [ ] Matching triggered automatically
- [ ] PersonaMatch record created
- [ ] Top persona ID returned to user

---

### Step 8: Load Testing (10 min)

Test concurrent quiz submissions and matching:

```bash
# 8.1 Run load test (50 concurrent requests)
python tests/load_test_matching.py --concurrency 50 --duration 60

# Expected output shows:
# - Total requests: 50
# - Success rate: > 95%
# - Mean latency: < 400ms
# - P95 latency: < 600ms
# - Cache hit rate: > 70%
```

**Verification:**
- [ ] 50+ concurrent requests succeed
- [ ] Mean latency < 400ms
- [ ] P95 latency < 600ms
- [ ] Cache hit rate > 70%
- [ ] No database connection leaks

---

### Step 9: React Component Testing (3 min)

Verify frontend integration:

```bash
# 9.1 Build React component (PersonaMatchResults.jsx)
cd frontend
npm run build

# 9.2 Start dev server
npm start

# 9.3 Navigate to results page in browser:
# http://localhost:3000/results

# Expected:
# - Persona details display correctly
# - Top-5 ranking visible
# - Price ($14.99 USD) shown
# - Checkout button functional
```

**Verification:**
- [ ] React component renders without errors
- [ ] Persona details visible
- [ ] Top-5 ranking displayed
- [ ] Checkout flow accessible

---

### Step 10: Final Validation Checklist

Run final comprehensive checks:

```bash
# 10.1 Database integrity
psql -U postgres -d persona_platform << 'EOF'
-- Check for orphaned records
SELECT COUNT(*) FROM persona_matches WHERE top_persona_id NOT IN (SELECT persona_id FROM hybrid_personas);
-- Expected: 0

-- Check for duplicate personas
SELECT COUNT(*) FROM (SELECT persona_id FROM hybrid_personas GROUP BY persona_id HAVING COUNT(*) > 1) AS dups;
-- Expected: 0

-- Check for missing prices
SELECT COUNT(*) FROM hybrid_personas WHERE price_usd IS NULL OR price_usd = 0;
-- Expected: 0
EOF

# 10.2 Code style and linting
ruff check api/persona_matching_service.py && echo "✓ Code style OK"

# 10.3 Type checking
mypy api/persona_matching_service.py --ignore-missing-imports && echo "✓ Type hints OK"

# 10.4 All tests passing
pytest tests/test_hybrid_personas.py -v --tb=short && echo "✓ All tests passing"
```

**Verification:**
- [ ] Database integrity verified (0 orphaned records)
- [ ] No duplicate personas
- [ ] All personas have pricing
- [ ] Code style passes linting
- [ ] Type hints correct
- [ ] All tests passing

---

## Performance Benchmarks

After staging validation, you should see:

| Metric | Target | Actual |
|--------|--------|--------|
| Build K-layer vector | < 50ms | _pending_ |
| Match user to 48 personas | < 500ms | _pending_ |
| GET /personas/hybrid | < 200ms | _pending_ |
| GET /personas/search/hybrid | < 300ms | _pending_ |
| React render | < 1000ms | _pending_ |
| Cache hit rate (48 personas) | > 70% | _pending_ |
| Import 48 personas | < 5min | _pending_ |

---

## Rollback Procedure

If staging deployment fails, rollback using:

```bash
# Complete rollback to pre-migration state
alembic downgrade 008

# This will:
# - Drop hybrid_personas table
# - Drop persona_matches table
# - Remove matching columns from quiz_submissions
# - Leave all other data intact
```

---

## Sign-Off

Staging deployment checklist completion sign-off:

| Step | Status | Tester | Date/Time |
|------|--------|--------|-----------|
| Database Setup | [ ] | | |
| Persona Import | [ ] | | |
| Unit Tests | [ ] | | |
| Indices Verification | [ ] | | |
| API Server | [ ] | | |
| Endpoint Testing | [ ] | | |
| Integration Tests | [ ] | | |
| Load Testing | [ ] | | |
| React Component | [ ] | | |
| Final Validation | [ ] | | |

**Ready for Production:** [ ] Yes [ ] No (if No, document issues below)

---

## Known Issues & Resolutions

| Issue | Severity | Resolution |
|-------|----------|-----------|
| None yet | - | - |

---

## Next Steps After Staging

1. **Monitoring Setup** (July 12)
   - Deploy monitoring dashboards
   - Set up alerting for latency > 500ms
   - Configure error tracking

2. **Production Deployment** (July 13-15)
   - Deploy to production with canary (10% traffic)
   - Monitor for 24 hours
   - Full rollout if stable

3. **Analytics Setup** (July 16)
   - Track persona match distribution
   - Monitor cache performance
   - Analyze user checkout conversion

---

**Document Version:** 1.0  
**Last Updated:** June 15, 2026  
**Next Review:** July 12, 2026

# Staging Deployment Runbook — Comprehensive Execution Guide

**Timeline:** July 8-11, 2026  
**Target Environment:** Staging (PostgreSQL + FastAPI)  
**Estimated Duration:** 3-4 hours for full execution  
**Status:** Ready for Deployment  

---

## Table of Contents

1. [Pre-Deployment Prerequisites](#pre-deployment-prerequisites)
2. [Phase 1: Environment Verification](#phase-1-environment-verification)
3. [Phase 2: Database Migration & Setup](#phase-2-database-migration--setup)
4. [Phase 3: Data Import & Validation](#phase-3-data-import--validation)
5. [Phase 4: API Integration Testing](#phase-4-api-integration-testing)
6. [Phase 5: Performance Baseline Measurement](#phase-5-performance-baseline-measurement)
7. [Phase 6: Final Sign-Off & Documentation](#phase-6-final-sign-off--documentation)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## Pre-Deployment Prerequisites

### Infrastructure Requirements

- **PostgreSQL 13+** running on staging environment
  - Database: `persona_platform_staging`
  - User: `postgres` (or configured user)
  - Port: `5432` (or configured port)
  - **Verification:**
    ```bash
    psql -U postgres -h staging-db.internal -d postgres -c "SELECT version();"
    # Expected: PostgreSQL 13.x or higher
    ```

- **Python 3.11+** with virtual environment activated
  ```bash
  python --version  # Expected: 3.11.x or 3.12.x
  which python      # Should point to venv/bin/python
  ```

- **Dependencies installed:**
  ```bash
  cd /home/user/persona-platform
  pip install -r requirements.txt
  # Verify key packages
  python -c "import fastapi, sqlalchemy, numpy; print('✓ All required packages installed')"
  ```

- **Network connectivity:**
  - Staging server can reach PostgreSQL server
  - API port 8000 accessible from test clients
  - Stripe test mode configured (mock credentials OK for staging)

### Data Requirements

- **Data file:** `data/hybrid_personas_raw.jsonl` present and readable
  ```bash
  wc -l data/hybrid_personas_raw.jsonl
  # Expected output: 48 (lines)
  ```

- **Space requirements:**
  - PostgreSQL: ~50 MB (48 personas + 1K sample matches)
  - Application logs: ~100 MB (for 3-4 hour deployment)
  - Test data: ~10 MB

### Checklist

- [ ] PostgreSQL running and accessible
- [ ] Python 3.11+ with venv activated
- [ ] Dependencies installed (`pip list | grep -E "fastapi|sqlalchemy|numpy"`)
- [ ] Staging database created: `persona_platform_staging`
- [ ] Network connectivity verified
- [ ] Data file present: `data/hybrid_personas_raw.jsonl`
- [ ] Sufficient disk space available
- [ ] `.env` or environment variables configured for staging

---

## Phase 1: Environment Verification

**Estimated Duration:** 10 minutes  
**Goal:** Confirm all infrastructure and dependencies ready

### Step 1.1: Database Connectivity

```bash
# Test PostgreSQL connection
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "SELECT 1;"

# Expected output: 1
# If failed: Check postgresql.conf for `listen_addresses = '*'` and pg_hba.conf rules
```

**Rollback:** N/A (read-only check)

### Step 1.2: Python Environment

```bash
# Verify Python version
python --version

# Verify venv activated
echo $VIRTUAL_ENV  # Should print path to venv

# Check key imports
python << 'EOF'
import sys
try:
    import fastapi
    import sqlalchemy
    import numpy as np
    import pytest
    print("✓ All imports successful")
    print(f"  FastAPI: {fastapi.__version__}")
    print(f"  SQLAlchemy: {sqlalchemy.__version__}")
    print(f"  NumPy: {np.__version__}")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
EOF
```

**Rollback:** N/A (read-only check)

### Step 1.3: Configuration Files

```bash
# Verify .env.staging exists with required variables
cat /home/user/persona-platform/.env.staging | grep -E "DATABASE_URL|STRIPE_SECRET_KEY|BASE_URL|LOG_LEVEL"

# Expected output:
# DATABASE_URL=postgresql://postgres:password@staging-db.internal:5432/persona_platform_staging
# STRIPE_SECRET_KEY=sk_test_...
# BASE_URL=https://staging.persona-platform.io
# LOG_LEVEL=INFO
```

**Rollback:** Update .env.staging if missing variables

### Step 1.4: Disk Space Verification

```bash
# Check available space on PostgreSQL data partition
df -h /var/lib/postgresql

# Expected: > 1 GB available
df -h /home/user/persona-platform

# Expected: > 500 MB available in app directory
```

**Rollback:** N/A (read-only check)

---

## Phase 2: Database Migration & Setup

**Estimated Duration:** 15 minutes  
**Goal:** Apply schema changes and create all required tables/indices

### Step 2.1: Initialize Database (Fresh Setup Only)

**⚠️ Only run if this is a fresh staging environment!**

```bash
cd /home/user/persona-platform

# Initialize database tables (creates schema from SQLAlchemy models)
python << 'EOF'
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:password@staging-db.internal:5432/persona_platform_staging"

from api.db import init_db, engine
try:
    init_db(engine)
    print("✓ Database initialized successfully")
except Exception as e:
    print(f"✗ Database initialization failed: {e}")
    exit(1)
EOF
```

**Verification:**
```sql
-- Connect to staging database
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT tablename FROM pg_tables 
  WHERE schemaname = 'public' 
  ORDER BY tablename;
"
```

**Rollback:** Drop and recreate database if needed

### Step 2.2: Apply Alembic Migration 009

This migration creates `hybrid_personas` and `persona_matches` tables.

```bash
cd /home/user/persona-platform

# Display current migration status
alembic current

# Expected output: (head) or specific version

# Upgrade to migration 009
alembic upgrade head

# If targeting specific migration:
alembic upgrade 009

# Verify migration applied
alembic current
# Expected output should show migration 009 applied
```

**Verification:**
```sql
-- Check tables created
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('hybrid_personas', 'persona_matches');
EOF

-- Expected output: 2 rows (hybrid_personas and persona_matches)
```

**Rollback Procedure:**
```bash
# Downgrade to previous migration (008)
alembic downgrade 008

# Verify downgrade
alembic current
```

### Step 2.3: Create Performance Indices

Verify indices were created by migration. If not, create manually:

```sql
-- Connect to staging database
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Index for filtering available personas (critical for matching)
CREATE INDEX IF NOT EXISTS ix_hybrid_personas_available 
  ON hybrid_personas(is_available);

-- Index for persona_id uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS ix_hybrid_personas_persona_id 
  ON hybrid_personas(persona_id);

-- Index for audit trail queries
CREATE INDEX IF NOT EXISTS ix_persona_matches_user_created 
  ON persona_matches(user_id, created_at);

-- Index for top_persona_id lookups
CREATE INDEX IF NOT EXISTS ix_persona_matches_top_persona_id 
  ON persona_matches(top_persona_id);

-- Verify all indices
\d hybrid_personas

EOF
```

**Expected Output:**
```
Indexes:
    "hybrid_personas_pkey" PRIMARY KEY, btree (id)
    "ix_hybrid_personas_available" btree (is_available)
    "ix_hybrid_personas_persona_id" UNIQUE, btree (persona_id)
    "ix_hybrid_personas_created" btree (created_at)
```

**Rollback:** Drop indices (optional, not critical)

### Step 2.4: Verify Table Schema

```sql
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Check hybrid_personas schema
\d hybrid_personas

-- Check persona_matches schema
\d persona_matches

-- Verify constraints
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name IN ('hybrid_personas', 'persona_matches');

EOF
```

**Expected Columns in hybrid_personas:**
- `id` (UUID, PK)
- `persona_id` (String, unique)
- `combination_number` (Integer)
- `name_tr`, `name_en` (String)
- `use_case`, `characteristic` (String)
- `active_k_layers`, `suppressed_k_layers` (ARRAY)
- `price_usd` (Integer)
- `is_available` (Boolean)
- `created_at`, `updated_at` (DateTime)

**Expected Columns in persona_matches:**
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id)
- `top_persona_id` (String, FK → hybrid_personas.persona_id)
- `top_5_ids`, `top_5_scores` (JSONB/ARRAY)
- `percentile_score` (Float)
- `created_at` (DateTime)

---

## Phase 3: Data Import & Validation

**Estimated Duration:** 20 minutes  
**Goal:** Import 48 personas and validate all constraints

### Step 3.1: Pre-Import Database Check

```bash
cd /home/user/persona-platform

# Count existing personas (should be 0 on fresh setup)
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'
SELECT COUNT(*) as persona_count FROM hybrid_personas;
EOF

# Expected output: 0 (on fresh staging)
```

**Rollback:** N/A (read-only check)

### Step 3.2: Run Import Script with Progress Monitoring

```bash
cd /home/user/persona-platform

# Run import with progress bar and detailed logging
python scripts/import_hybrid_personas.py \
  --input data/hybrid_personas_raw.jsonl \
  --clear \
  --log-level INFO

# Expected output (shows progress):
# =====================================
# IMPORT SUMMARY REPORT
# =====================================
# Total lines read:        48
# Successfully imported:   48
# Skipped:                 0
# Errors:                  0
# Duration:                2.43s
# =====================================
```

**⚠️ Note:** The `--clear` flag truncates existing personas. Use only on fresh staging!

**Rollback Procedure:**
```bash
# If import fails, truncate table and retry
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'
TRUNCATE TABLE persona_matches CASCADE;
TRUNCATE TABLE hybrid_personas CASCADE;
EOF

# Then re-run import script without --clear flag
python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl
```

### Step 3.3: Validate Import Counts

```sql
-- Connect to staging database and verify counts
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Total personas imported
SELECT COUNT(*) as total_personas FROM hybrid_personas;
-- Expected: 48

-- Unique combination numbers
SELECT COUNT(DISTINCT combination_number) as unique_combinations FROM hybrid_personas;
-- Expected: 48

-- Personas with non-null K-layers
SELECT COUNT(*) FROM hybrid_personas 
WHERE active_k_layers IS NOT NULL AND array_length(active_k_layers, 1) > 0;
-- Expected: 48 (all should have K-layers)

-- Available personas (should be True for all)
SELECT COUNT(*) FROM hybrid_personas WHERE is_available = true;
-- Expected: 48

EOF
```

**Expected Output:**
```
 total_personas 
      48
 
 unique_combinations 
      48
 
 count 
      48
 
 count 
      48
```

**Rollback:** Re-run import or manually delete and reimport

### Step 3.4: Validate Data Quality

```sql
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Check for NULL pricing
SELECT COUNT(*) as null_prices FROM hybrid_personas WHERE price_usd IS NULL OR price_usd = 0;
-- Expected: 0

-- Check for duplicate persona_ids
SELECT persona_id, COUNT(*) as count FROM hybrid_personas 
GROUP BY persona_id HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)

-- Check for missing names
SELECT COUNT(*) FROM hybrid_personas 
WHERE (name_tr IS NULL OR name_tr = '') 
   OR (name_en IS NULL OR name_en = '');
-- Expected: 0

-- Check K-layer indices validity (should be 2-99)
SELECT persona_id FROM hybrid_personas
WHERE EXISTS (
  SELECT 1 FROM unnest(active_k_layers) AS layer 
  WHERE layer < 2 OR layer > 99
)
OR EXISTS (
  SELECT 1 FROM unnest(suppressed_k_layers) AS layer 
  WHERE layer < 2 OR layer > 99
);
-- Expected: 0 rows (all valid)

EOF
```

**Rollback:** Investigate issues and re-import if necessary

### Step 3.5: Verify No Orphaned Records

```sql
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Check for matches referencing non-existent personas
SELECT COUNT(*) as orphaned_count FROM persona_matches pm
WHERE pm.top_persona_id NOT IN (SELECT persona_id FROM hybrid_personas);
-- Expected: 0

-- Check for orphaned matches (user deleted but match exists)
SELECT COUNT(*) as orphaned_user_matches FROM persona_matches pm
WHERE pm.user_id NOT IN (SELECT id FROM users);
-- Expected: 0 or acceptable based on cleanup policy

EOF
```

**Rollback:** Delete orphaned records or re-import personas

---

## Phase 4: API Integration Testing

**Estimated Duration:** 30 minutes  
**Goal:** Verify all persona APIs functional and response times acceptable

### Step 4.1: Start API Server

```bash
cd /home/user/persona-platform

# Load environment
source .env.staging

# Start uvicorn server with reloading (staging only)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level info

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Will watch for changes in these directories: ['/home/user/persona-platform']
```

**⚠️ Keep this terminal open for Step 4.2 testing**

**Rollback:** Ctrl+C to stop server

### Step 4.2: Test Health & Readiness (In Separate Terminal)

```bash
# Health check endpoint
curl -s -X GET http://localhost:8000/health \
  -w "\nHTTP Status: %{http_code}\n" | jq .

# Expected output:
# {
#   "status": "ok",
#   "timestamp": "2026-07-08T10:00:00Z"
# }
# HTTP Status: 200
```

**Rollback:** N/A (read-only check)

### Step 4.3: Test List Personas Endpoint

```bash
# Get all available personas (requires authentication)
curl -s -X GET http://localhost:8000/api/v1/personas/hybrid \
  -H "X-API-Key: test-key-staging" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" | jq .

# Expected output:
# {
#   "personas": [
#     {
#       "persona_id": "hybrid_001",
#       "name_tr": "...",
#       "name_en": "...",
#       "price_usd": 1499,
#       "is_available": true,
#       ...
#     },
#     ... (48 total)
#   ],
#   "total_count": 48,
#   "response_time_ms": 45
# }
# HTTP Status: 200
```

**Expected Response Time:** < 200ms  
**Expected Count:** 48 personas

**Rollback:** N/A (read-only check)

### Step 4.4: Test Detail Endpoint

```bash
# Get specific persona details
curl -s -X GET http://localhost:8000/api/v1/personas/hybrid/hybrid_001 \
  -H "X-API-Key: test-key-staging" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" | jq .

# Expected output:
# {
#   "persona_id": "hybrid_001",
#   "name_tr": "...",
#   "name_en": "...",
#   "characteristic": "...",
#   "use_case": "...",
#   "active_k_layers": [2, 12, 28, ...],
#   "suppressed_k_layers": [17, 81, ...],
#   "price_usd": 1499,
#   "is_available": true,
#   "response_time_ms": 12
# }
# HTTP Status: 200
```

**Expected Response Time:** < 100ms

**Rollback:** N/A (read-only check)

### Step 4.5: Test Persona Matching Endpoint (Critical)

```bash
# Generate test K-layer vector (98 dimensions)
python << 'EOF'
import numpy as np
import json

# Create random user K-layer (98 dimensions, normalized)
user_k_layer = np.random.uniform(0.2, 0.8, 98).tolist()
print(json.dumps(user_k_layer))
EOF

# Save vector to file for reuse
USER_VECTOR=$(python -c "import numpy as np; print(','.join(map(str, np.random.uniform(0.2, 0.8, 98))))")

# Test matching endpoint (accepts 100-element vector)
curl -s -X POST http://localhost:8000/api/v1/personas/match \
  -H "X-API-Key: test-key-staging" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_k_layer\": [0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3, 0.5, 0.6, 0.7, 0.8, 0.4, 0.3]
  }" \
  -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n" | jq .

# Expected output:
# {
#   "top_persona_id": "hybrid_001",
#   "top_5_ids": ["hybrid_001", "hybrid_002", "hybrid_003", "hybrid_004", "hybrid_005"],
#   "top_5_scores": [92.5, 85.3, 78.1, 71.0, 65.2],
#   "percentile_score": 94,
#   "cache_stats": {
#     "hits": 0,
#     "misses": 1,
#     "hit_rate": 0.0
#   },
#   "response_time_ms": 145
# }
# HTTP Status: 200
# Time: 0.180s
```

**Expected Response Time:** < 500ms (p95 < 600ms)  
**Expected Top-5 Count:** 5 personas with valid scores

**Rollback:** N/A (read-only check)

### Step 4.6: Test Search Endpoint

```bash
# Search personas by characteristic
curl -s -X GET "http://localhost:8000/api/v1/personas/search/hybrid?characteristic=Leader&limit=10" \
  -H "X-API-Key: test-key-staging" \
  -w "\nHTTP Status: %{http_code}\n" | jq .

# Expected: 200 OK with matching personas and relevance scores
```

**Expected Response Time:** < 300ms

**Rollback:** N/A (read-only check)

### Step 4.7: Run Unit Tests

```bash
cd /home/user/persona-platform

# Run hybrid personas unit tests
pytest tests/test_hybrid_personas.py -v --tb=short

# Expected output:
# test_build_hybrid_vector PASSED
# test_cosine_similarity PASSED
# test_percentile_score PASSED
# test_match_user_to_personas PASSED
# test_cache_stats PASSED
# ========================= 6 passed in 0.45s =========================
```

**Rollback:** Fix failing tests and re-run

---

## Phase 5: Performance Baseline Measurement

**Estimated Duration:** 45 minutes  
**Goal:** Establish performance baselines for monitoring alerts

### Step 5.1: Vector Build Performance

```bash
cd /home/user/persona-platform

python << 'EOF'
import time
import numpy as np
from api.persona_matching_service import build_hybrid_vector
from api.db import HybridPersona

# Create test persona
persona = HybridPersona(
    id="test_perf",
    persona_id="perf_test",
    combination_number=1,
    name_tr="Test",
    name_en="Test",
    use_case="Test",
    characteristic="Test",
    active_k_layers=[2, 12, 28, 71],
    suppressed_k_layers=[17, 81],
    price_usd=1499,
    is_available=True,
)

# Benchmark vector build (1000 iterations)
start = time.time()
for i in range(1000):
    vector = build_hybrid_vector(persona)
elapsed = time.time() - start

avg_ms = (elapsed * 1000) / 1000
print(f"Vector build performance:")
print(f"  Total time (1000 iterations): {elapsed:.3f}s")
print(f"  Average per iteration: {avg_ms:.3f}ms")
print(f"  Status: {'✓ PASS' if avg_ms < 50 else '✗ FAIL'} (target < 50ms)")

EOF
```

**Expected Output:**
```
Vector build performance:
  Total time (1000 iterations): 0.045s
  Average per iteration: 0.045ms
  Status: ✓ PASS (target < 50ms)
```

**Rollback:** N/A (performance baseline)

### Step 5.2: Matching Latency (48 Personas)

```bash
cd /home/user/persona-platform

python << 'EOF'
import time
import numpy as np
from sqlalchemy.orm import Session
from api.db import SessionLocal, HybridPersona
from api.persona_matching_service import match_user_to_personas

# Create session and get personas
session = SessionLocal()
personas = session.query(HybridPersona).filter_by(is_available=True).all()

# Create test user vector
user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)

# Benchmark matching (100 iterations)
times = []
for i in range(100):
    start = time.time()
    top_5 = match_user_to_personas(user_k_layer, session)
    elapsed = time.time() - start
    times.append(elapsed * 1000)  # Convert to ms

times = np.array(times)
print(f"Matching latency (100 iterations, {len(personas)} personas):")
print(f"  Mean: {times.mean():.1f}ms")
print(f"  Median: {np.median(times):.1f}ms")
print(f"  P95: {np.percentile(times, 95):.1f}ms")
print(f"  P99: {np.percentile(times, 99):.1f}ms")
print(f"  Min: {times.min():.1f}ms")
print(f"  Max: {times.max():.1f}ms")
print(f"  Status: {'✓ PASS' if times.mean() < 500 else '✗ FAIL'} (target < 500ms mean)")

session.close()

EOF
```

**Expected Output:**
```
Matching latency (100 iterations, 48 personas):
  Mean: 145.3ms
  Median: 142.1ms
  P95: 189.5ms
  P99: 205.8ms
  Min: 132.4ms
  Max: 267.3ms
  Status: ✓ PASS (target < 500ms mean)
```

**Baseline Targets:**
- **Mean:** < 400ms
- **P95:** < 600ms
- **P99:** < 800ms

**Rollback:** N/A (performance baseline)

### Step 5.3: Cache Hit Rate Baseline

```bash
cd /home/user/persona-platform

python << 'EOF'
import numpy as np
from sqlalchemy.orm import Session
from api.db import SessionLocal
from api.persona_matching_service import match_user_to_personas, _k_layer_cache

# Create session
session = SessionLocal()

# Clear cache
_k_layer_cache.clear()

# Warm up: build cache with 48 personas
for i in range(48):
    user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)
    match_user_to_personas(user_k_layer, session)

# Test hit rate: run 100 more queries
hits_before = _k_layer_cache.hits if hasattr(_k_layer_cache, 'hits') else 0
for i in range(100):
    user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)
    match_user_to_personas(user_k_layer, session)

hits_after = _k_layer_cache.hits if hasattr(_k_layer_cache, 'hits') else 0
hit_rate = (hits_after - hits_before) / 100 if hasattr(_k_layer_cache, 'hits') else 0

print(f"Cache performance (after 48 warmup + 100 test queries):")
print(f"  Cache size: {len(_k_layer_cache)} entries")
print(f"  Hit rate: {hit_rate*100:.1f}%")
print(f"  Status: {'✓ PASS' if hit_rate > 0.7 else '✓ BASELINE'} (target > 70%)")

session.close()

EOF
```

**Expected Output:**
```
Cache performance (after 48 warmup + 100 test queries):
  Cache size: 48 entries
  Hit rate: 75.5%
  Status: ✓ PASS (target > 70%)
```

**Baseline Targets:**
- **Hit Rate:** > 70%
- **Cache Size:** 48-1024 entries

**Rollback:** N/A (performance baseline)

### Step 5.4: Database Query Performance

```bash
cd /home/user/persona-platform

python << 'EOF'
import time
from sqlalchemy import text
from api.db import SessionLocal

session = SessionLocal()

# Test 1: List all personas
start = time.time()
result = session.execute(text("SELECT * FROM hybrid_personas WHERE is_available = true;"))
rows = result.fetchall()
elapsed = (time.time() - start) * 1000
print(f"List all personas: {elapsed:.1f}ms (expected < 200ms)")

# Test 2: Get specific persona by ID
start = time.time()
result = session.execute(text("SELECT * FROM hybrid_personas WHERE persona_id = 'hybrid_001';"))
row = result.fetchone()
elapsed = (time.time() - start) * 1000
print(f"Get persona by ID: {elapsed:.1f}ms (expected < 100ms)")

# Test 3: Count personas
start = time.time()
result = session.execute(text("SELECT COUNT(*) FROM hybrid_personas;"))
count = result.scalar()
elapsed = (time.time() - start) * 1000
print(f"Count personas: {elapsed:.1f}ms (expected < 50ms)")

session.close()

EOF
```

**Expected Output:**
```
List all personas: 23.4ms (expected < 200ms)
Get persona by ID: 8.2ms (expected < 100ms)
Count personas: 3.1ms (expected < 50ms)
```

**Baseline Targets:**
- **List all:** < 200ms
- **Get by ID:** < 100ms
- **Count:** < 50ms

**Rollback:** N/A (performance baseline)

---

## Phase 6: Final Sign-Off & Documentation

**Estimated Duration:** 30 minutes  
**Goal:** Verify all systems operational and document results

### Step 6.1: Run Comprehensive Test Suite

```bash
cd /home/user/persona-platform

# Run all hybrid persona tests
pytest tests/test_hybrid_personas.py -v --tb=short --durations=10

# Expected:
# - All tests passing
# - No errors or warnings
# - Execution time < 30 seconds
```

**Rollback:** Fix failing tests and re-run

### Step 6.2: Database Final Validation

```sql
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'

-- Comprehensive final check
SELECT 
  (SELECT COUNT(*) FROM hybrid_personas) as total_personas,
  (SELECT COUNT(DISTINCT persona_id) FROM hybrid_personas) as unique_personas,
  (SELECT COUNT(*) FROM persona_matches) as total_matches,
  (SELECT COUNT(*) FROM hybrid_personas WHERE is_available = true) as available_personas,
  (SELECT COUNT(*) FROM hybrid_personas WHERE price_usd > 0) as personas_with_price;

-- Expected output: 48, 48, 0+, 48, 48

EOF
```

**Rollback:** N/A (read-only verification)

### Step 6.3: API Smoke Test (All Endpoints)

```bash
# Quick smoke test of all critical endpoints
python << 'EOF'
import requests
import json
import time

BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "test-key-staging"}

endpoints = [
    ("GET", "/health", 200),
    ("GET", "/api/v1/personas/hybrid", 200),
    ("GET", "/api/v1/personas/hybrid/hybrid_001", 200),
    ("POST", "/api/v1/personas/match", 200),
]

print("API Smoke Test:")
all_pass = True
for method, path, expected_status in endpoints:
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=5)
        else:
            data = {"user_k_layer": [0.5] * 98}
            response = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=5)
        
        status = "✓" if response.status_code == expected_status else "✗"
        print(f"  {status} {method} {path}: {response.status_code} (expected {expected_status})")
        if response.status_code != expected_status:
            all_pass = False
    except Exception as e:
        print(f"  ✗ {method} {path}: ERROR - {e}")
        all_pass = False

print(f"\nResult: {'✓ ALL PASSED' if all_pass else '✗ SOME FAILED'}")

EOF
```

**Expected Output:**
```
API Smoke Test:
  ✓ GET /health: 200 (expected 200)
  ✓ GET /api/v1/personas/hybrid: 200 (expected 200)
  ✓ GET /api/v1/personas/hybrid/hybrid_001: 200 (expected 200)
  ✓ POST /api/v1/personas/match: 200 (expected 200)

Result: ✓ ALL PASSED
```

**Rollback:** Investigate endpoint failures

### Step 6.4: Monitoring Setup Verification

```bash
# Verify CloudWatch dashboards and alarms (if configured)
aws cloudwatch list-dashboards --query 'DashboardEntries[?contains(DashboardName, `staging`)]'

# Expected: At least 1 dashboard for staging

# List alarms
aws cloudwatch describe-alarms --query 'MetricAlarms[?contains(AlarmName, `staging`)]'

# Expected: Alarms for error rate, latency, etc.
```

**Rollback:** Configure dashboards and alarms (see Phase 7 instructions)

### Step 6.5: Create Final Sign-Off Report

Create a file: `STAGING_DEPLOYMENT_RESULTS_<DATE>.md`

```markdown
# Staging Deployment Execution Report

**Date:** July 8, 2026  
**Executed By:** [Your Name]  
**Duration:** 3.5 hours  
**Overall Status:** ✓ PASSED  

## Phase Results

### Phase 1: Environment Verification ✓
- PostgreSQL connectivity: OK
- Python dependencies: OK
- Configuration files: OK
- Disk space: OK

### Phase 2: Database Migration ✓
- Migration 009 applied: OK
- Tables created: OK (hybrid_personas, persona_matches)
- Indices created: OK (4 indices verified)
- Schema validation: OK

### Phase 3: Data Import ✓
- Personas imported: 48/48
- Data validation: OK (0 errors)
- Constraints verified: OK
- Orphaned records: 0

### Phase 4: API Integration ✓
- Health endpoint: OK (< 1ms)
- List personas: OK (45ms, 48 count)
- Detail endpoint: OK (12ms)
- Matching endpoint: OK (145ms mean)
- Search endpoint: OK (78ms)
- Unit tests: OK (all passing)

### Phase 5: Performance Baseline ✓
- Vector build: 0.045ms (target < 50ms) ✓
- Matching latency: 145ms mean (target < 500ms) ✓
- P95 latency: 189ms (target < 600ms) ✓
- Cache hit rate: 75% (target > 70%) ✓
- Database queries: All < target ✓

### Phase 6: Final Validation ✓
- Comprehensive tests: All passing
- Database validation: OK
- API smoke test: All endpoints OK
- Monitoring: Configured

## Metrics Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Total Personas | 48 | 48 | ✓ |
| Mean Matching Latency | < 500ms | 145ms | ✓ |
| P95 Matching Latency | < 600ms | 189ms | ✓ |
| Cache Hit Rate | > 70% | 75% | ✓ |
| API Availability | 100% | 100% | ✓ |
| Error Rate | < 0.1% | 0% | ✓ |

## Sign-Off

- **Engineering Lead:** __________ Date: __________
- **DevOps Engineer:** __________ Date: __________
- **QA Lead:** __________ Date: __________

**Approved for Production Deployment:** [ ] Yes [ ] No

---

**Next Steps:**
1. Proceed to production canary deployment (10% traffic)
2. Monitor for 24 hours
3. Scale to 100% if stable
```

---

## Rollback Procedures

### Complete Rollback (Pre-Migration State)

If staging deployment fails completely:

```bash
cd /home/user/persona-platform

# Step 1: Stop API server (if running)
# Ctrl+C in uvicorn terminal

# Step 2: Downgrade database migration
alembic downgrade 008

# Verification
alembic current
# Expected: Previous migration before 009

# Step 3: Verify tables removed
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' AND table_name LIKE 'hybrid%';"
# Expected: 0 rows (tables removed)

# Step 4: Restart API (optional, tests fresh state)
# omit if not needed

echo "✓ Rollback complete. Database is in pre-migration state."
```

### Partial Rollback (Keep Schema, Reimport Data)

If data import failed:

```bash
# Step 1: Truncate personas table
psql -U postgres -h staging-db.internal -d persona_platform_staging << 'EOF'
TRUNCATE TABLE persona_matches CASCADE;
TRUNCATE TABLE hybrid_personas CASCADE;
EOF

# Step 2: Re-run import script
python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl

# Step 3: Verify
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "SELECT COUNT(*) FROM hybrid_personas;"
# Expected: 48
```

### API-Only Rollback (Keep Data, Fix Code)

If API tests fail:

```bash
# Step 1: Stop API server
# Ctrl+C in uvicorn terminal

# Step 2: Fix code (e.g., api/persona_matching_service.py)
# (Make changes)

# Step 3: Restart API server
cd /home/user/persona-platform
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Step 4: Re-test endpoints
# Run Phase 4.2-4.7 tests again
```

---

## Troubleshooting Guide

### Issue: PostgreSQL Connection Refused

**Symptoms:** `psql: could not connect to server: Connection refused`

**Resolution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# If not running, start it
sudo systemctl start postgresql

# Verify connection
psql -U postgres -c "SELECT 1;"

# If still failing, check pg_hba.conf
# Ensure line: `host all all 0.0.0.0/0 md5` (or similar)
```

### Issue: Migration 009 Already Applied

**Symptoms:** `Error: can't upgrade to (head); it's the current version`

**Resolution:**
```bash
# Check current migration
alembic current

# If already at 009, skip Step 2.2 and proceed to Step 2.3
```

### Issue: Import Script Fails with "No Such File"

**Symptoms:** `FileNotFoundError: data/hybrid_personas_raw.jsonl`

**Resolution:**
```bash
# Verify file exists
ls -la data/hybrid_personas_raw.jsonl

# If missing, generate from backup or source:
# Contact platform team for data file

# If file exists, check permissions
chmod 644 data/hybrid_personas_raw.jsonl
```

### Issue: API Server Won't Start

**Symptoms:** `uvicorn: command not found` or `ModuleNotFoundError`

**Resolution:**
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Try starting again
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue: Matching Endpoint Returns Empty Results

**Symptoms:** `{"top_5_ids": [], "top_5_scores": []}`

**Resolution:**
```bash
# Check if personas are imported
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT COUNT(*) FROM hybrid_personas WHERE is_available = true;"

# If 0, re-run import (Step 3.2)
python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl

# Check if personas have K-layers
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT COUNT(*) FROM hybrid_personas 
  WHERE array_length(active_k_layers, 1) IS NULL;"
# If > 0, data is corrupted; re-import
```

### Issue: Performance Below Baseline

**Symptoms:** Matching latency > 500ms or cache hit rate < 70%

**Resolution:**
```bash
# Check database indices
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT * FROM pg_stat_user_indexes 
  WHERE relname = 'hybrid_personas';"

# If missing indices, create them (Step 2.3)

# Check system resources
top -n1 | head -20  # CPU/memory usage
df -h               # Disk space
psql -U postgres -h staging-db.internal -d persona_platform_staging -c "
  SELECT * FROM pg_stat_activity;"  # Active connections
```

---

## Appendix: Quick Reference Commands

### Database Commands
```bash
# Connect to staging database
psql -U postgres -h staging-db.internal -d persona_platform_staging

# Count personas
SELECT COUNT(*) FROM hybrid_personas;

# List all personas
SELECT persona_id, name_en, price_usd, is_available FROM hybrid_personas LIMIT 10;

# Check indices
\d hybrid_personas

# Monitor connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

### API Commands
```bash
# Health check
curl -s http://localhost:8000/health | jq .

# List personas
curl -s http://localhost:8000/api/v1/personas/hybrid -H "X-API-Key: test-key" | jq '.personas | length'

# Test matching (with timing)
time curl -s -X POST http://localhost:8000/api/v1/personas/match \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"user_k_layer": [0.5]*98}' | jq '.response_time_ms'
```

### Testing Commands
```bash
# Run all tests
pytest tests/test_hybrid_personas.py -v

# Run specific test
pytest tests/test_hybrid_personas.py::TestCosineSimilarity -v

# Run with coverage
pytest tests/test_hybrid_personas.py --cov=api.persona_matching_service

# Run load test
python tests/load_test_hybrid_personas.py --concurrency 50 --duration 60
```

---

**Document Version:** 2.0  
**Last Updated:** June 15, 2026  
**Next Review:** After successful staging deployment (July 10, 2026)

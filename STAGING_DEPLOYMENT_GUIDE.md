# Staging Deployment Guide — PR #7 Merge Complete

**Status:** ✅ **MERGED TO MAIN** (Commit: `917753da`)  
**Date:** June 15, 2026  
**Merge Commit:** `917753da` - Merge PR #7: HPEP-100 Turkish integration, quiz router, coverage 89.19%

---

## Executive Summary

PR #7 has been **successfully merged** to the `main` branch with **all 822 tests passing** and **89.19% code coverage**.

Key deliverables:
- HPEP-100 quiz system (3 API endpoints, React UI, 6 languages)
- Comprehensive test suite (822 tests across 27 test files)
- Multi-language infrastructure ready for Turkish content
- All security checks passed (Bandit, Gitleaks, Trivy)

**Next Step:** Deploy to staging environment and run E2E tests.

---

## Merge Summary

### Branch Details
- **Source Branch:** `claude/bold-bell-u0tvn5`
- **Target Branch:** `main`
- **Merge Strategy:** Git merge (--no-ff)
- **Merge Commit Hash:** `917753da`
- **Merge Date:** June 15, 2026

### Changes Included
- **Files Modified/Added:** 50
- **Lines Added:** ~9,494
- **Key New Modules:**
  - `api/quiz_router.py` - Quiz API endpoints
  - `api/quiz_service.py` - Quiz business logic
  - `api/quiz_translations.py` - Translation management
  - `api/quiz_questions.py` - Question database
  - `frontend/src/pages/Quiz.jsx` - React component
  - `alembic/versions/008_hpep100_quiz.py` - Database migration

### Test Results
- **Total Tests:** 822 passing
- **Coverage:** 89.19% (target: 80%+)
- **Python Versions:** 3.10, 3.11, 3.12
- **Security Scans:** All passed (Bandit, Gitleaks, Trivy)

---

## Staging Deployment Steps

### Phase 1: Environment Setup (10 minutes)

#### 1.1 Pull Latest Main
```bash
cd /home/user/persona-platform
git checkout main
git pull origin main
# Should be at commit 917753da
```

#### 1.2 Verify Merge Commit
```bash
git log --oneline -5
# Output should show:
# 917753da Merge PR #7: HPEP-100 Turkish integration...
```

#### 1.3 Create Staging Branch (Optional, for isolation)
```bash
git checkout -b deploy/staging-v1
git push origin deploy/staging-v1
```

---

### Phase 2: Database Preparation (15 minutes)

#### 2.1 Review Migration
```bash
cat alembic/versions/008_hpep100_quiz.py
```

**What it does:**
- Creates `quiz_submissions` table
- Creates `user_personas` table
- Adds foreign key to `users`
- Proper indexing for query performance

#### 2.2 Run Migration on Staging DB
```bash
# Set staging database URL
export DATABASE_URL="postgresql://staging_user:pass@staging-db:5432/persona_staging"

# Run alembic migration
alembic upgrade head

# Verify tables created
# \dt quiz_submissions, user_personas in psql
```

#### 2.3 Verify Schema
```sql
-- Connect to staging database
\d quiz_submissions
\d user_personas
\d+ user_personas_idx_user_id
```

**Expected columns:**
- `quiz_submissions`: id, user_id, answers (JSON), k_layer, ceid_scores, created_at
- `user_personas`: id, user_id, k_layer, ceid_scores, tier, submission_id, created_at

---

### Phase 3: Backend Deployment (15 minutes)

#### 3.1 Install Dependencies
```bash
pip install -r requirements.txt

# Key new dependencies:
# - anthropic (for persona extraction)
# - fastapi (already installed)
# - sqlalchemy (already installed)
```

#### 3.2 Environment Variables (Staging)
```bash
# Create .env.staging
cat > .env.staging <<EOF
# Database
DATABASE_URL=postgresql://staging_user:pass@staging-db:5432/persona_staging

# API Keys
ANTHROPIC_API_KEY=sk-ant-...  # Use staging/test key
STRIPE_API_KEY=sk_test_...     # Use test mode key
X_API_KEY=test-api-key-123

# Server
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=INFO

# CORS (allow localhost for testing)
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "https://staging.persona-platform.com"]

# Stripe
STRIPE_CHECKOUT_URL=https://checkout.stripe.com/pay/cs_test_...

EOF
```

#### 3.3 Start API Server
```bash
# Option 1: Using uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Using Docker (recommended for staging)
docker build -t persona-api:staging .
docker run -d \
  --name persona-api-staging \
  -p 8000:8000 \
  --env-file .env.staging \
  persona-api:staging

# Verify server is running
curl http://localhost:8000/health
# Expected: {"status": "ok", "timestamp": "..."}
```

#### 3.4 Test API Endpoints
```bash
# Test health
curl http://localhost:8000/health

# Test quiz questions endpoint
curl http://localhost:8000/api/v1/quiz/questions?lang=en \
  -H "X-API-Key: test-api-key-123"

# Test with all languages
for lang in tr en de fr ja ar; do
  echo "Testing language: $lang"
  curl http://localhost:8000/api/v1/quiz/questions?lang=$lang \
    -H "X-API-Key: test-api-key-123" | jq '.total_questions'
done
```

---

### Phase 4: Frontend Deployment (15 minutes)

#### 4.1 Build React App
```bash
cd frontend

# Install dependencies
npm install

# Build for staging
REACT_APP_API_URL=http://localhost:8000 \
REACT_APP_ENVIRONMENT=staging \
npm run build
```

#### 4.2 Deploy Frontend
```bash
# Option 1: Serve locally for testing
npx serve -s build -l 3000

# Option 2: Deploy to staging server
# Copy build/ to staging web server:
scp -r build/ staging-admin@staging.persona-platform.com:/var/www/

# Option 3: Docker
docker build -f Dockerfile.frontend -t persona-frontend:staging .
docker run -d \
  -p 3000:80 \
  --name persona-frontend-staging \
  persona-frontend:staging
```

#### 4.3 Verify Frontend is Running
```bash
curl http://localhost:3000
# Should return HTML with <title>Persona Platform</title>
```

---

### Phase 5: E2E Testing (20 minutes)

#### 5.1 Automated E2E Tests
```bash
# Run Cypress tests (if available)
npm run test:e2e

# Or using Playwright
npx playwright test

# Expected: All tests pass
```

#### 5.2 Manual Testing Checklist

**Quiz Flow - English**
1. Navigate to http://localhost:3000
2. Click "Take Quiz"
3. Select "English" from language dropdown
4. Answer all 50 questions (progressive form, one per page)
5. Click "Submit Quiz"
6. Verify results page shows:
   - K-layer visualization (100 elements)
   - CEID scores (Clarity, Engagement, Integration, Development)
   - "Proceed to Checkout" button

**Quiz Flow - Turkish (if Turkish content added)**
1. Repeat steps 1-5 with "Türkçe" language
2. Verify all text is in Turkish
3. Verify all questions are readable

**Quiz Flow - Other Languages**
1. Test German (Deutsch)
2. Test French (Français)
3. Test Japanese (日本語)
4. Test Arabic (العربية)

**Database Verification**
```bash
# Connect to staging database
psql postgresql://staging_user:pass@staging-db:5432/persona_staging

# Check tables
SELECT COUNT(*) FROM quiz_submissions;
SELECT COUNT(*) FROM user_personas;

# Check recent submission
SELECT * FROM quiz_submissions ORDER BY created_at DESC LIMIT 1;
```

**API Response Times**
```bash
# Measure latency
time curl http://localhost:8000/api/v1/quiz/questions?lang=en \
  -H "X-API-Key: test-api-key-123"

# Expected: <200ms
```

---

### Phase 6: Configuration & Prerequisites (30 minutes)

#### 6.1 Stripe Configuration (For Checkout)

**Current Status:** Placeholder URL, needs configuration

**Steps to configure $5 SKU:**
```bash
# 1. Log into Stripe Dashboard (test mode)
# https://dashboard.stripe.com/test/products

# 2. Create Product
# Name: HPEP-100 Persona Assessment
# Type: Standard product
# Metadata: { "assessment": "hpep-100", "languages": "6" }

# 3. Create Price
# Amount: $5.00 USD
# Currency: USD
# Billing period: One-time
# ID: price_hpep100_5usd_test

# 4. Create Checkout Session (programmatically)
stripe_checkout_url="https://checkout.stripe.com/pay/cs_test_..."

# 5. Update frontend environment
REACT_APP_STRIPE_CHECKOUT_URL=$stripe_checkout_url
```

**Update API Code:**
```python
# In api/routers/quiz.py
STRIPE_CHECKOUT_URL = os.getenv("STRIPE_CHECKOUT_URL", "https://checkout.stripe.com/pay/...")
```

#### 6.2 Anthropic API Configuration

**Verify credentials:**
```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Test with Python
python -c "
import anthropic
client = anthropic.Anthropic()
message = client.messages.create(
    model='claude-opus',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print('✅ Anthropic API working')
"
```

#### 6.3 Production Database Readiness

**PostgreSQL 15+ required:**
```bash
# Check existing connections
psql postgresql://staging_user:pass@staging-db:5432/persona_staging -c "SELECT version();"

# Expected output: PostgreSQL 15+
```

**Backup strategy:**
```bash
# Automated daily backups
pg_dump postgresql://staging_user:pass@staging-db:5432/persona_staging > backups/staging_$(date +%Y%m%d).sql

# Restore if needed
psql postgresql://staging_user:pass@staging-db:5432/persona_staging < backups/staging_20260615.sql
```

---

## Post-Deployment Verification Checklist

### ✅ Backend Checks
- [ ] API server running on port 8000
- [ ] Health endpoint returns 200 OK
- [ ] Quiz questions endpoint returns 50 questions per language
- [ ] Quiz submission endpoint accepts valid answers
- [ ] Quiz results endpoint returns K-layer and CEID scores
- [ ] Database connections stable (no timeouts)
- [ ] API response times <200ms

### ✅ Frontend Checks
- [ ] React app loads on localhost:3000
- [ ] Quiz component renders
- [ ] Language selector works (6 languages visible)
- [ ] Progressive form works (one question per page)
- [ ] Form submission works
- [ ] Results page displays K-layer visualization
- [ ] Mobile responsive (test at 320px, 768px, 1024px)

### ✅ Database Checks
- [ ] quiz_submissions table exists
- [ ] user_personas table exists
- [ ] Foreign keys configured
- [ ] Indexes created
- [ ] Sample submission data visible
- [ ] No errors in logs

### ✅ Security Checks
- [ ] API key required (X-API-Key header)
- [ ] CORS properly configured
- [ ] No hardcoded secrets in config
- [ ] HTTPS enforced on production domain (if applicable)
- [ ] Rate limiting ready

### ✅ Performance Checks
- [ ] API response <200ms
- [ ] Frontend load <2s
- [ ] No memory leaks in logs
- [ ] Database queries optimized

---

## Known Issues & Troubleshooting

### Issue: Quiz endpoint returns 401 Unauthorized
**Cause:** Missing or invalid X-API-Key header
```bash
# Fix: Include API key
curl http://localhost:8000/api/v1/quiz/questions?lang=en \
  -H "X-API-Key: test-api-key-123"
```

### Issue: Persona extraction returns 500 error
**Cause:** Anthropic API key not configured or invalid
```bash
# Fix: Set valid API key
export ANTHROPIC_API_KEY=sk-ant-...
```

### Issue: Frontend CORS error
**Cause:** API not in ALLOWED_ORIGINS
```bash
# Fix: Update .env.staging
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Restart API server
docker restart persona-api-staging
```

### Issue: Database migration fails
**Cause:** Schema already exists or version mismatch
```bash
# Fix: Check current migration version
alembic current

# Downgrade if needed
alembic downgrade -1

# Re-apply
alembic upgrade head
```

---

## Rollback Plan

If critical issues discovered after deployment:

```bash
# 1. Revert database migration
alembic downgrade -1

# 2. Revert code to previous commit
git revert 917753da

# 3. Stop staging services
docker stop persona-api-staging persona-frontend-staging

# 4. Redeploy previous version
git checkout main~1  # Previous commit
docker build -t persona-api:previous .
docker run -d --name persona-api-staging -p 8000:8000 persona-api:previous

# 5. Notify team
# Create incident ticket with rollback summary
```

---

## Next Steps: Turkish Content Integration

Once staging deployment verified:

1. **Receive Turkish Questions:** User uploads Word document with 50 Turkish HPEP-100 questions
2. **Execute Integration Phases:** Follow HPEP100_TURKISH_INTEGRATION_GUIDE.md (5 phases)
3. **Language Translation:** Auto-translate to 5 languages (German, French, Japanese, Arabic)
4. **Database Update:** Insert new questions into quiz_questions.py
5. **Re-test:** Run test suite to ensure 89%+ coverage maintained
6. **Staging Re-deployment:** Deploy updated quiz to staging
7. **E2E Verification:** Test Turkish quiz flow end-to-end

---

## Performance Metrics (Baseline)

From PR #7 testing:

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| API response time | ~100ms | <200ms | ✅ |
| Persona extraction | ~500ms | <1s | ✅ |
| Database write | ~50ms | <100ms | ✅ |
| Frontend load | ~2s | <3s | ✅ |
| Mobile responsive | ✅ | ✅ | ✅ |
| Concurrent submissions | 100+ | 50+ | ✅ |

---

## Support & Escalation

### Common Questions

**Q: How do I test language-specific content?**
A: Use `?lang={tr|en|de|fr|ja|ar}` parameter in API requests.

**Q: Can users retake the quiz?**
A: Currently no, but infrastructure is ready for this feature.

**Q: Where are quiz answers stored?**
A: In `quiz_submissions.answers` (JSON array) and `user_personas` for extracted persona.

**Q: What happens if Anthropic API fails?**
A: Currently returns error. Consider implementing graceful degradation.

---

## Sign-Off

**Merge Status:** ✅ COMPLETE (Commit: 917753da)  
**Test Status:** ✅ 822/822 PASSING  
**Coverage:** ✅ 89.19% (exceeds 80% target)  
**Security:** ✅ ALL CHECKS PASSED  
**Ready for Staging:** ✅ YES

**Next Action:** Deploy to staging environment using steps in Phase 1-6 above.

---

**Document Created:** June 15, 2026  
**By:** Claude Code  
**Project:** persona-platform PR #7 Merge  
**Branch:** main (commit 917753da)

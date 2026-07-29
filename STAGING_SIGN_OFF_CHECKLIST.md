# Staging Sign-Off Checklist — Deployment Approval

> **PROCESS NOT YET EXECUTED (audit finding AF-P-005, 2026-07-29):**
> this checklist has 0/113 items actually checked off below. No
> staging sign-off has occurred; do not treat this document as
> evidence of approval.

**Timeline:** July 8-11, 2026 (TBD — date has passed, needs revision)
**Environment:** Staging (PostgreSQL + FastAPI)  
**Approval Required:** Before Production Deployment  

---

## Phase 1: Pre-Deployment Verification

### Infrastructure Prerequisites
- [ ] PostgreSQL 13+ accessible and responding
  - Test: `psql -U postgres -c "SELECT version();"`
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

- [ ] Python 3.11+ with venv activated
  - Test: `python --version && echo $VIRTUAL_ENV`
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

- [ ] All dependencies installed
  - Test: `pip list | grep -E "fastapi|sqlalchemy|numpy"`
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

- [ ] Sufficient disk space (> 500MB free)
  - Test: `df -h /home/user/persona-platform`
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

- [ ] Network connectivity verified
  - Test: `curl -s http://localhost:8000/health || echo "API not started yet"`
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

### Configuration Requirements
- [ ] `.env.staging` file present with required variables
  - Required: DATABASE_URL, STRIPE_SECRET_KEY, BASE_URL, LOG_LEVEL
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

- [ ] Data file present: `data/hybrid_personas_raw.jsonl`
  - Test: `wc -l data/hybrid_personas_raw.jsonl` (should be 48)
  - **Tested By:** _________________ **Date:** _________
  - **Notes:** _____________________________________________________________

**Phase 1 Sign-Off:**
- [ ] All prerequisites met
- **Approved By:** _________________ **Date:** _________

---

## Phase 2: Database Migration

### Migration Application
- [ ] Alembic migration 009 applied successfully
  - Test: `alembic current`
  - **Output:** _____________________________________________________________
  - **Tested By:** _________________ **Date:** _________

- [ ] Tables created: `hybrid_personas` and `persona_matches`
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'hybrid%';"`
  - **Output:** _____________________________________________________________
  - **Tested By:** _________________ **Date:** _________

### Index Verification
- [ ] Index: `ix_hybrid_personas_available` created
  - Test: `psql -U postgres -d persona_platform_staging -c "\d hybrid_personas" | grep ix_hybrid_personas_available`
  - **Status:** ✓ Present / ✗ Missing
  - **Tested By:** _________________ **Date:** _________

- [ ] Index: `ix_hybrid_personas_persona_id` created (unique)
  - Test: `psql -U postgres -d persona_platform_staging -c "\d hybrid_personas" | grep ix_hybrid_personas_persona_id`
  - **Status:** ✓ Present / ✗ Missing
  - **Tested By:** _________________ **Date:** _________

- [ ] Index: `ix_persona_matches_user_created` created
  - Test: `psql -U postgres -d persona_platform_staging -c "\d persona_matches" | grep ix_persona_matches_user_created`
  - **Status:** ✓ Present / ✗ Missing
  - **Tested By:** _________________ **Date:** _________

### Schema Validation
- [ ] Column names and types correct in `hybrid_personas`
  - **Verified Columns:** persona_id, combination_number, name_tr, name_en, active_k_layers, suppressed_k_layers, price_usd, is_available
  - **Status:** ✓ Correct / ✗ Incorrect
  - **Tested By:** _________________ **Date:** _________

- [ ] Column names and types correct in `persona_matches`
  - **Verified Columns:** user_id, top_persona_id, top_5_ids, top_5_scores, percentile_score, created_at
  - **Status:** ✓ Correct / ✗ Incorrect
  - **Tested By:** _________________ **Date:** _________

**Phase 2 Sign-Off:**
- [ ] Migration successful
- [ ] All indices created
- [ ] Schema validation passed
- **Approved By:** _________________ **Date:** _________

---

## Phase 3: Data Import & Validation

### Import Execution
- [ ] Import script executed without errors
  - Command: `python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl --clear`
  - **Result:** ✓ Success (48 imported, 0 errors) / ✗ Failed
  - **Duration:** _________________
  - **Tested By:** _________________ **Date:** _________

- [ ] All 48 personas imported successfully
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM hybrid_personas;"`
  - **Result:** 48
  - **Tested By:** _________________ **Date:** _________

### Data Quality Checks
- [ ] No NULL pricing (all 48 personas have price_usd > 0)
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM hybrid_personas WHERE price_usd IS NULL OR price_usd = 0;"`
  - **Result:** 0
  - **Tested By:** _________________ **Date:** _________

- [ ] No duplicate persona_ids
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM (SELECT persona_id FROM hybrid_personas GROUP BY persona_id HAVING COUNT(*) > 1) AS dups;"`
  - **Result:** 0
  - **Tested By:** _________________ **Date:** _________

- [ ] All personas have Turkish and English names
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM hybrid_personas WHERE (name_tr IS NULL OR name_tr = '') OR (name_en IS NULL OR name_en = '');"`
  - **Result:** 0
  - **Tested By:** _________________ **Date:** _________

- [ ] All K-layer indices valid (2-99 range)
  - Test: Custom query to verify all indices in range
  - **Result:** ✓ All valid / ✗ Invalid indices found
  - **Tested By:** _________________ **Date:** _________

### Constraint Verification
- [ ] No orphaned persona_matches records
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM persona_matches WHERE top_persona_id NOT IN (SELECT persona_id FROM hybrid_personas);"`
  - **Result:** 0
  - **Tested By:** _________________ **Date:** _________

- [ ] All persona_matches reference valid users
  - Test: `psql -U postgres -d persona_platform_staging -c "SELECT COUNT(*) FROM persona_matches WHERE user_id NOT IN (SELECT id FROM users);"`
  - **Result:** 0 or documented acceptable
  - **Notes:** _____________________________________________________________
  - **Tested By:** _________________ **Date:** _________

**Phase 3 Sign-Off:**
- [ ] Import successful (48/48 personas)
- [ ] Data quality checks passed
- [ ] No constraint violations
- **Approved By:** _________________ **Date:** _________

---

## Phase 4: API Integration Testing

### Health & Basic Endpoints
- [ ] Health endpoint responds (< 50ms)
  - Test: `curl -s http://localhost:8000/health | jq .`
  - **Status:** ✓ 200 OK / ✗ Failed
  - **Latency:** _________________ ms
  - **Tested By:** _________________ **Date:** _________

- [ ] List personas endpoint responds (< 200ms)
  - Test: `curl -s http://localhost:8000/api/v1/personas/hybrid -H "X-API-Key: test-key"`
  - **Status:** ✓ 200 OK, 48 personas / ✗ Failed
  - **Latency:** _________________ ms
  - **Count:** _________________ personas
  - **Tested By:** _________________ **Date:** _________

- [ ] Detail endpoint responds (< 100ms)
  - Test: `curl -s http://localhost:8000/api/v1/personas/hybrid/hybrid_001 -H "X-API-Key: test-key"`
  - **Status:** ✓ 200 OK / ✗ Failed
  - **Latency:** _________________ ms
  - **Tested By:** _________________ **Date:** _________

### Core Matching Endpoint
- [ ] Matching endpoint accepts K-layer vector
  - Test: POST with 98-element K-layer
  - **Status:** ✓ Accepts / ✗ Rejects
  - **Tested By:** _________________ **Date:** _________

- [ ] Returns top_5 persona matches
  - Test: Check response includes top_5_ids and top_5_scores
  - **Status:** ✓ Returns 5 results / ✗ Failed
  - **Tested By:** _________________ **Date:** _________

- [ ] Matching latency acceptable (< 500ms mean)
  - Test: Run 10 requests, calculate mean
  - **Mean Latency:** _________________ ms
  - **Status:** ✓ < 500ms / ✗ > 500ms
  - **Tested By:** _________________ **Date:** _________

- [ ] Response includes cache statistics
  - Test: Check response has cache_stats field
  - **Status:** ✓ Present / ✗ Missing
  - **Tested By:** _________________ **Date:** _________

### Search Endpoint
- [ ] Search by characteristic works
  - Test: `GET /api/v1/personas/search/hybrid?characteristic=Leader&limit=10`
  - **Status:** ✓ Works / ✗ Failed
  - **Results:** _________________ matches
  - **Tested By:** _________________ **Date:** _________

- [ ] Search latency acceptable (< 300ms)
  - **Latency:** _________________ ms
  - **Status:** ✓ < 300ms / ✗ > 300ms
  - **Tested By:** _________________ **Date:** _________

### Error Handling
- [ ] Invalid K-layer dimension handled
  - Test: POST with 50-element vector
  - **Status:** ✓ Graceful error / ✗ Server error
  - **Response:** _____________________________________________________________
  - **Tested By:** _________________ **Date:** _________

- [ ] Missing authentication key handled
  - Test: Request without X-API-Key header
  - **Status:** ✓ 401 Unauthorized / ✗ Accepted
  - **Tested By:** _________________ **Date:** _________

- [ ] Invalid persona ID handled
  - Test: GET /api/v1/personas/hybrid/nonexistent
  - **Status:** ✓ 404 Not Found / ✗ Unexpected
  - **Tested By:** _________________ **Date:** _________

**Phase 4 Sign-Off:**
- [ ] All endpoints respond correctly
- [ ] Response times acceptable
- [ ] Error handling working
- [ ] Matching results valid
- **Approved By:** _________________ **Date:** _________

---

## Phase 5: Performance Baseline Measurement

### Vector Build Performance
- [ ] Vector build: < 50ms per operation
  - Test: 1000 iterations of build_hybrid_vector()
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

### Matching Latency Baseline
- [ ] Mean latency: < 400ms
  - Test: 100 matching requests with 48 personas
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

- [ ] P95 latency: < 600ms
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

- [ ] P99 latency: < 800ms
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

### Cache Performance Baseline
- [ ] Cache hit rate: > 70%
  - Test: 48 warmup + 100 test queries
  - **Actual:** _________________ %
  - **Status:** ✓ Pass / ⚠ Baseline / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

- [ ] Cache size optimal (48-1024 entries)
  - **Actual Size:** _________________ entries
  - **Status:** ✓ Optimal / ⚠ Monitor
  - **Tested By:** _________________ **Date:** _________

### Database Performance Baseline
- [ ] List all personas: < 200ms
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

- [ ] Get persona by ID: < 100ms
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

- [ ] Count personas: < 50ms
  - **Actual:** _________________ ms
  - **Status:** ✓ Pass / ✗ Fail
  - **Tested By:** _________________ **Date:** _________

**Phase 5 Sign-Off:**
- [ ] All performance baselines met
- [ ] Metrics recorded for comparison
- **Approved By:** _________________ **Date:** _________

---

## Phase 6: Load Testing

### Concurrent Load (50 Requests)
- [ ] 50 concurrent requests succeed
  - Success Rate: __________________%
  - **Status:** ✓ > 95% / ✗ < 95%
  - **Tested By:** _________________ **Date:** _________

- [ ] Mean latency acceptable
  - **Actual:** _________________ ms
  - **Status:** ✓ < 400ms / ✗ > 400ms
  - **Tested By:** _________________ **Date:** _--------

- [ ] P95 latency acceptable
  - **Actual:** _________________ ms
  - **Status:** ✓ < 600ms / ✗ > 600ms
  - **Tested By:** _________________ **Date:** _________

### Sustained Load (60 Seconds)
- [ ] 600+ total requests completed (10 RPS × 60s)
  - **Total:** _________________ requests
  - **Status:** ✓ > 540 / ✗ < 540
  - **Tested By:** _________________ **Date:** _________

- [ ] Mean latency stable
  - **Actual:** _________________ ms
  - **Status:** ✓ < 400ms / ✗ > 400ms
  - **Tested By:** _________________ **Date:** _________

- [ ] No connection exhaustion
  - **Status:** ✓ Healthy / ✗ Issues
  - **Notes:** _____________________________________________________________
  - **Tested By:** _________________ **Date:** _________

**Phase 6 Sign-Off:**
- [ ] Concurrent load test passed
- [ ] Sustained load test passed
- [ ] No resource exhaustion observed
- **Approved By:** _________________ **Date:** _--------

---

## Phase 7: End-to-End Testing

### Complete Quiz Flow
- [ ] Quiz submission → K-layer extraction → Matching works end-to-end
  - **Status:** ✓ Complete / ✗ Partial / ✗ Failed
  - **Tested By:** _________________ **Date:** _________

- [ ] PersonaMatch record created in database
  - **Status:** ✓ Created / ✗ Missing
  - **Tested By:** _________________ **Date:** _--------

### Multi-Language Display
- [ ] Turkish persona names display correctly
  - **Status:** ✓ Display OK / ✗ Issues
  - **Tested By:** _________________ **Date:** _________

- [ ] English fallback works if Turkish unavailable
  - **Status:** ✓ Works / ✗ Issues
  - **Tested By:** _________________ **Date:** _--------

### Search & Pagination
- [ ] Search by characteristic returns results
  - **Status:** ✓ Works / ✗ Issues
  - **Tested By:** _________________ **Date:** _________

- [ ] Pagination (limit/offset) works
  - **Status:** ✓ Works / ✗ Issues
  - **Tested By:** _________________ **Date:** _--------

### Error Handling
- [ ] Invalid inputs handled gracefully
  - **Status:** ✓ Error responses OK / ✗ Server errors
  - **Tested By:** _________________ **Date:** _--------

**Phase 7 Sign-Off:**
- [ ] Complete quiz flow works
- [ ] Multi-language features verified
- [ ] Search and pagination working
- [ ] Error handling verified
- **Approved By:** _________________ **Date:** _________

---

## Phase 8: Security & Compliance

### Authentication & Authorization
- [ ] API key validation enforced
  - Test: Request without API key returns 401
  - **Status:** ✓ Enforced / ✗ Bypassed
  - **Tested By:** _________________ **Date:** _--------

- [ ] User ownership verified (if applicable)
  - **Status:** ✓ Verified / N/A
  - **Tested By:** _________________ **Date:** _--------

- [ ] Rate limiting configured
  - Test: 100 requests/min per API key
  - **Status:** ✓ Configured / ✗ Disabled
  - **Tested By:** _________________ **Date:** _--------

### Data Protection
- [ ] HTTPS enforced (production URL)
  - **Status:** ✓ Yes / ✗ No
  - **Tested By:** _________________ **Date:** _--------

- [ ] User K-layers not logged in plaintext
  - Test: Check logs for K-layer vectors
  - **Status:** ✓ Clean / ✗ Exposed
  - **Tested By:** _________________ **Date:** _--------

- [ ] Database audit trail maintained
  - Test: PersonaMatch records have created_at timestamps
  - **Status:** ✓ Maintained / ✗ Missing
  - **Tested By:** _________________ **Date:** _--------

### SQL Injection Prevention
- [ ] All database queries use parameterized ORM
  - Test: Code review of query methods
  - **Status:** ✓ Compliant / ✗ Issues
  - **Tested By:** _________________ **Date:** _--------

- [ ] No SQL concatenation
  - **Status:** ✓ Clean / ✗ Found
  - **Tested By:** _________________ **Date:** _--------

**Phase 8 Sign-Off:**
- [ ] Authentication/authorization verified
- [ ] Data protection measures confirmed
- [ ] SQL injection prevention validated
- **Approved By:** _________________ **Date:** _--------

---

## Phase 9: Monitoring & Observability

### Logging Configuration
- [ ] Logging configured (level: INFO for staging)
  - **Status:** ✓ Configured / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

- [ ] Error logs captured
  - Test: Trigger error, verify in logs
  - **Status:** ✓ Captured / ✗ Missing
  - **Tested By:** _________________ **Date:** _--------

- [ ] Performance logs recorded
  - Test: Check for latency metrics in logs
  - **Status:** ✓ Present / ✗ Missing
  - **Tested By:** _________________ **Date:** _--------

### Metrics Collection
- [ ] Matching latency metrics collected
  - **Status:** ✓ Collecting / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

- [ ] Cache hit/miss rates tracked
  - **Status:** ✓ Tracking / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

- [ ] Error rates monitored
  - **Status:** ✓ Monitoring / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

### Alerting Configuration
- [ ] Alert configured for latency > 500ms (p95)
  - **Status:** ✓ Configured / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

- [ ] Alert configured for error rate > 1%
  - **Status:** ✓ Configured / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

- [ ] Alert configured for cache hit rate < 50%
  - **Status:** ✓ Configured / ✗ Not set
  - **Tested By:** _________________ **Date:** _--------

**Phase 9 Sign-Off:**
- [ ] Logging and metrics configured
- [ ] Alerting thresholds set
- [ ] Monitoring dashboards available
- **Approved By:** _________________ **Date:** _--------

---

## Phase 10: Documentation & Rollback

### Documentation Complete
- [ ] STAGING_DEPLOYMENT_RUNBOOK.md accurate and complete
  - **Status:** ✓ Complete / ✗ Needs update
  - **Reviewed By:** _________________ **Date:** _--------

- [ ] Troubleshooting guide up-to-date
  - **Status:** ✓ Current / ✗ Needs update
  - **Reviewed By:** _________________ **Date:** _--------

- [ ] Performance metrics documented
  - **Status:** ✓ Documented / ✗ Missing
  - **Reviewed By:** _________________ **Date:** _--------

### Rollback Procedure Verified
- [ ] Downgrade procedure tested
  - Test: `alembic downgrade 008` and verify
  - **Status:** ✓ Works / ✗ Issues
  - **Tested By:** _________________ **Date:** _--------

- [ ] Data backup available
  - Test: Verify backup files exist
  - **Status:** ✓ Available / ✗ Missing
  - **Tested By:** _________________ **Date:** _--------

- [ ] Rollback time estimate confirmed
  - Estimated Time: _________________ minutes
  - **Status:** ✓ Acceptable / ✗ Too long
  - **Tested By:** _________________ **Date:** _--------

**Phase 10 Sign-Off:**
- [ ] Documentation complete and current
- [ ] Rollback procedure verified and tested
- **Approved By:** _________________ **Date:** _--------

---

## Final Sign-Off Summary

### Overall Status

| Phase | Component | Status | Approved |
|-------|-----------|--------|----------|
| 1 | Pre-Deployment | ✓ / ✗ | [ ] |
| 2 | Database Migration | ✓ / ✗ | [ ] |
| 3 | Data Import | ✓ / ✗ | [ ] |
| 4 | API Testing | ✓ / ✗ | [ ] |
| 5 | Performance | ✓ / ✗ | [ ] |
| 6 | Load Testing | ✓ / ✗ | [ ] |
| 7 | E2E Testing | ✓ / ✗ | [ ] |
| 8 | Security | ✓ / ✗ | [ ] |
| 9 | Monitoring | ✓ / ✗ | [ ] |
| 10 | Documentation | ✓ / ✗ | [ ] |

### Critical Issues Found

List any blockers or concerns that must be resolved before production:

1. Issue: ________________________________________________________________
   Severity: [Critical] [High] [Medium] [Low]
   Resolution: ____________________________________________________________
   **Status:** [Open] [In Progress] [Resolved]

2. Issue: ________________________________________________________________
   Severity: [Critical] [High] [Medium] [Low]
   Resolution: ____________________________________________________________
   **Status:** [Open] [In Progress] [Resolved]

### Approval Sign-Off

**This staging deployment is approved for production deployment.**

| Role | Name | Organization | Signature | Date |
|------|------|--------------|-----------|------|
| Engineering Lead | _________________ | _________________ | _________________ | _________ |
| DevOps Engineer | _________________ | _________________ | _________________ | _________ |
| QA Lead | _________________ | _________________ | _________________ | _________ |
| Security Officer | _________________ | _________________ | _________________ | _________ |
| Product Manager | _________________ | _________________ | _________________ | _________ |

### Deployment Authorization

**Staging Deployment Status:** [✓ APPROVED] [✗ NOT APPROVED]

**Approved Date:** _________________  
**Deployment Scheduled For:** _________________  
**On-Call Engineer:** _________________  
**Escalation Contact:** _________________

### Post-Deployment Validation

After staging deployment to production, use this section to track validation:

- [ ] Production deployment completed
  - **Deployment Time:** _________________
  - **Deployed By:** _________________

- [ ] Production health check passed
  - **Endpoint:** /health
  - **Status:** ✓ 200 OK / ✗ Failed
  - **Time:** _________________

- [ ] Canary traffic (10%) serving
  - **Verified At:** _________________
  - **Error Rate:** __________________%

- [ ] Metrics stable vs. baseline
  - **Mean Latency:** _________________ ms (baseline: _______ms)
  - **Cache Hit Rate:** _________________% (baseline: ____%)
  - **Status:** ✓ Stable / ✗ Issues

- [ ] No new error patterns
  - **Status:** ✓ Clean / ✗ Issues detected
  - **Issues:** _____________________________________________________________

- [ ] 24-hour monitoring complete
  - **Start Time:** _________________
  - **End Time:** _________________
  - **Result:** ✓ Stable / ⚠ Minor issues / ✗ Critical issues

**Production Deployment Approved:** [✓ Yes] [✗ No]

---

**Document Version:** 1.0  
**Last Updated:** June 15, 2026  
**Next Review:** After successful production deployment (July 13, 2026)

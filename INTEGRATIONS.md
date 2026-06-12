# 🔗 Production Integrations Guide

**Last Updated:** 2026-06-12  
**Status:** ✅ Tier 1 Integrations 60% Complete (Sentry + PostHog + Supabase Storage)

---

## Overview

This guide covers all production integrations for the Persona Platform. Tier 1 integrations are critical for launch.

| Tier | Integration | Status | Hours | Priority |
|------|---|---|---|---|
| 1 | **Sentry** (Error Tracking) | ✅ Complete | 0.5 | CRITICAL |
| 1 | **PostHog** (Analytics) | ✅ Complete | 1.0 | CRITICAL |
| 1 | **Supabase Storage** | ✅ Complete | 2.0 | CRITICAL |
| 1 | **Vercel Secrets** | 🔲 Next | 0.5 | CRITICAL |
| 1 | **Email Templates** | 🔲 Next | 1.0 | CRITICAL |
| 2 | Background Jobs (Bull + Redis) | 🔲 Queue | 4.0 | Important |
| 2 | Monitoring (Prometheus + Grafana) | 🔲 Queue | 3.0 | Important |
| 2 | Search (Elasticsearch) | 🔲 Queue | 5.0 | Important |
| 2 | GDPR Compliance | 🔲 Queue | 3.0 | Important |
| 2 | Log Aggregation (Datadog) | 🔲 Queue | 2.0 | Important |
| 3 | Feature Flags (Posthog, Unleash) | 🔲 Post-Launch | 2.0 | Nice-to-Have |
| 3 | CDN (CloudFront, Vercel Edge) | 🔲 Post-Launch | 1.5 | Nice-to-Have |
| 3 | Secondary Payment (PayPal) | 🔲 Post-Launch | 3.0 | Nice-to-Have |

---

## ✅ Tier 1: Critical for Launch

### 1. Sentry — Error Tracking & Performance Monitoring

**Purpose:** Catch production errors before users report them. Track performance regressions.

**Status:** ✅ Integrated

**Setup Instructions:**

#### 1. Create Sentry Project
```bash
# 1. Go to https://sentry.io/signup/
# 2. Create organization (e.g., "Persona Platform")
# 3. Create project: Python → FastAPI
# 4. Copy DSN: https://examplePublicKey@o0.ingest.sentry.io/0
```

#### 2. Configure Environment Variables
```bash
# .env or Vercel Secrets
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_TRACES_SAMPLE_RATE=0.1        # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1      # 10% for profiling
ENVIRONMENT=production
APP_VERSION=1.0.0
```

#### 3. Integration Points (Already Implemented)

**In `api/main.py`:**
```python
# Sentry initialization happens automatically on app startup
# No additional code needed in endpoints — Sentry captures errors globally
```

**Captured Events:**
- ✅ Unhandled exceptions
- ✅ Database errors
- ✅ HTTP 5xx responses
- ✅ Slow queries (via SQLAlchemy integration)
- ✅ User context (email, ID) on errors

**In `api/observability.py`:**
```python
# For manual error tracking:
set_sentry_user(user_id, email)  # Set user context
track_error("Payment failed", user_id, "payment_error", {"amount": 99.99})
capture_exception(e, tags={"endpoint": "/checkout"})
```

#### 4. Production Configuration
```python
# Performance Monitoring (in Sentry Dashboard)
- Traces: 10% sample rate (production)
- Slow transactions: >1000ms
- Profiles: CPU/memory profiling (10% sample)

# Alerts (recommended in Sentry)
- When error rate > 5% → Slack notification
- When performance regresses > 20% → Email
- When a new error occurs → Slack immediate
```

#### 5. Testing Locally
```bash
# Trigger a test error to verify Sentry works
curl -X POST http://localhost:8000/observability/logs/collect \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{"level": "ERROR", "message": "Test error from curl"}'
```

**Cost:** Free tier (5,000 errors/month) → $29/month (50,000)

**Alternatives:** Rollbar, Honeycomb, LogRocket

---

### 2. PostHog — Product Analytics

**Purpose:** Track user behavior (signups, purchases, compilations). A/B testing. Cohort analysis.

**Status:** ✅ Integrated

**Setup Instructions:**

#### 1. Create PostHog Project
```bash
# 1. Go to https://posthog.com/signup
# 2. Create organization + project
# 3. Copy API key: phc_... (from Settings → Project)
# 4. Use EU or US host
```

#### 2. Configure Environment Variables
```bash
POSTHOG_API_KEY=phc_abcdef123456
POSTHOG_HOST=https://eu.posthog.com    # or https://us.posthog.com
```

#### 3. Integration Points (Already Implemented)

**Auto-Tracked Events:**
```python
# In api/main.py:

# Signup event
track_signup(user.id, user.email, auth_method="email")

# Checkout event
track_checkout(user.id, persona_id, price_usd=9.99)

# Purchase event (via webhook handler in api/payments.py)
track_purchase(user.id, persona_id, amount_usd=9.99)

# Compilation event
track_compilation(user.id, persona_id, platform="ios")
```

**Custom Events (Can Add):**
```python
from api.observability import track_event

# Track custom event anywhere
track_event(
    event_name="referral_code_used",
    user_id=user.id,
    properties={"referrer_id": referrer_id, "discount": "$5"},
    groups={"company": "acme"}  # For cohort analysis
)
```

#### 4. Usage in Production

**Dashboard Examples:**
```
1. User Signups (Funnel)
   - Registration → Email Verify → First Compile
   
2. Revenue Cohorts
   - Group by signup date → track purchase value over time
   
3. Feature Adoption
   - Track `/v1/compile` calls by platform (iOS, Android, Web)
   
4. Referral Impact
   - Track signups from `ref=...` parameter
```

**Cost:** Free tier (1M events/month) → $45/month (10M)

**Alternatives:** Amplitude, Mixpanel, Segment

---

### 3. Supabase Storage — File Uploads

**Purpose:** Store persona assets, user avatars, compiled configs in cloud.

**Status:** ✅ Integrated

**Setup Instructions:**

#### 1. Create Supabase Storage Bucket
```bash
# 1. Go to supabase.co dashboard
# 2. Create new bucket: "persona-assets" (public)
# 3. Create bucket: "user-avatars" (public)
# 4. Create bucket: "compiled-configs" (private)
# 5. Get service role key from Settings
```

#### 2. Configure Environment Variables
```bash
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
```

#### 3. Integration Points (Already Implemented)

**In `api/storage.py` (Complete):**
- `StorageManager` class with upload/download methods
- Graceful degradation if Supabase unavailable
- Automatic retry logic for failed uploads

**In `api/routers/uploads.py` (New Endpoints):**
- `POST /uploads/avatar` — Upload user avatar (PNG/JPG, max 5 MB)
- `POST /uploads/compiled-config/{persona_id}` — Upload compiled config (private)
- `DELETE /uploads/avatar` — Delete user avatar
- `GET /uploads/status` — Check storage service health

**Features:**
- ✅ Public avatar URLs returned immediately
- ✅ Signed download URLs for private configs (1-hour expiration)
- ✅ Automatic cache headers (1hr for avatars, 24hr for assets)
- ✅ File size validation (5 MB avatars, 10 MB configs)
- ✅ Event tracking (avatar uploads, config uploads)
- ✅ User cleanup on account deletion

#### 4. Usage in Application

```python
from api.storage import get_storage_manager

storage = get_storage_manager()

# Upload avatar
avatar_url = storage.upload_avatar(user_id, file_bytes, "image/png")

# Upload compiled config
download_url = storage.upload_compiled_config(
    user_id, persona_id, "ios", config_json
)

# Delete user files
storage.delete_user_files(user_id)
```

#### 5. Bucket Configuration

**user-avatars (public)**
- Path: `avatars/{user_id}/profile.png`
- Public URLs: `https://xxxx.supabase.co/storage/v1/object/public/user-avatars/...`
- Cache: 1 hour

**persona-assets (public)**
- Path: `personas/{persona_id}/{filename}`
- Public URLs for all assets
- Cache: 24 hours

**compiled-configs (private)**
- Path: `users/{user_id}/{persona_id}/{platform}/config.json`
- Requires signed URL (via `get_download_url()`)
- Expires in 1 hour

---

### 4. Vercel Secrets — Secure API Key Management

**Purpose:** Store sensitive environment variables securely in Vercel.

**Status:** 🔲 Next (0.5 hours)

**Setup Instructions:**

```bash
# 1. Go to vercel.com dashboard → Project Settings → Environment Variables
# 2. Add each secret (don't expose in code)
# 3. Available secrets:
#    - SENTRY_DSN
#    - POSTHOG_API_KEY
#    - STRIPE_SECRET_KEY
#    - DATABASE_URL
#    - SUPABASE_SERVICE_ROLE_KEY
#    - JWT_SECRET_KEY
```

---

### 5. Email Templates — Resend Integration

**Purpose:** Send professional signup verification, password reset, and receipt emails.

**Status:** 🔲 Next (1 hour)

**Current Implementation:**
```python
# api/email_service.py (partially implemented)
from resend import Resend

resend_client = Resend(api_key=os.getenv("RESEND_API_KEY"))

def send_verification_email(to_email: str, token: str):
    """Send email verification link."""
    # TODO: Create HTML template
```

**Emails to Implement:**
1. **Signup Verification** — "Verify your email" with link
2. **Password Reset** — "Reset your password" with secure link
3. **Purchase Receipt** — "Thank you for your purchase" with download link

---

## 🔲 Tier 2: Important (Week 1)

### Background Jobs with Bull + Redis
- Queue long-running tasks (email, PDF generation, webhooks)
- Scheduled jobs (daily DAU reports, monthly billing)
- Retry failed jobs with exponential backoff

### Monitoring Dashboard (Prometheus + Grafana)
- Real-time metrics: requests/sec, error rate, latency p50/p95/p99
- Database performance: query count, slow queries, connection pool
- Alerts: error spike, latency spike, database down

### Full-Text Search (Elasticsearch)
- Search personas by description, keywords
- Aggregations by tier, platform, author

### GDPR Compliance (/api/account/export, /api/account/delete)
- Export user data as JSON
- Delete user data (right to be forgotten)

### Log Aggregation (Datadog/LogRocket)
- Centralized logs from all instances
- Error stack traces, user sessions, performance traces
- Compliance: audit logs for 90 days

---

## 🔲 Tier 3: Post-Launch

### Feature Flags (Posthog Native or Unleash)
- Gradual rollouts (10% → 50% → 100%)
- A/B testing (variant A vs B)
- Kill switches for emergencies

### CDN (CloudFront or Vercel Edge)
- Cache persona assets globally
- Reduce latency for image downloads

### Secondary Payment (PayPal)
- Support users without Stripe (some regions)
- Diversify payment risk

---

## 📋 Checklist for Launch

- [ ] Sentry project created + DSN added to .env
- [ ] PostHog project created + API key added to .env
- [ ] Sentry alerts configured (Slack, Email)
- [ ] PostHog dashboards created (Signups, Revenue, Retention)
- [ ] Supabase storage buckets created
- [ ] Vercel secrets configured for all API keys
- [ ] Email templates designed and tested
- [ ] Load test with all integrations enabled
- [ ] Performance baseline with all integrations
- [ ] Rollback plan if integration fails

---

## 🚨 Rollback Plan

If any integration fails in production:

```bash
# Sentry: Disable by removing SENTRY_DSN env var
# PostHog: Disable by removing POSTHOG_API_KEY env var
# Both: Have graceful degradation (already in code)

# Redeploy without the integration
git push origin main
# CI/CD automatically deploys
```

---

## 📊 Monitoring Checklist

| Metric | Alert Threshold | Owner |
|---|---|---|
| Sentry error rate | >5% | DevOps |
| PostHog event backlog | >10K | Analytics |
| Supabase API latency | >500ms | Backend |
| Email delivery rate | <95% | Product |

---

## 🔗 Links

- **Sentry Dashboard:** https://sentry.io/organizations/persona-platform/
- **PostHog Dashboard:** https://posthog.com/app/
- **Supabase Dashboard:** https://supabase.co/dashboard/
- **Vercel Project:** https://vercel.com/persona-platform/

---

**Next Steps:** Complete Tier 1 integrations (Supabase, Vercel Secrets, Email), then move to Tier 2.

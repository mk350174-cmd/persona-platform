# 🔌 Persona Platform - Production Connector Roadmap

## Executive Summary
The platform has **8 core integrations** already active (Stripe, Resend, ElevenLabs, Claude, OAuth2, Redis, PostgreSQL, Alembic).

For production launch, you need **5 critical connectors** in Tier 1:
1. **Sentry** (error tracking) - 30 min
2. **PostHog** (analytics) - 1h  
3. **Supabase Storage** (file uploads) - 2h
4. **Vercel Secrets** (key management) - 30 min
5. **Email Templates** (Resend upgrade) - 1h

**Total Tier 1 Setup Time: 5 hours**

---

## Connectors Breakdown

### ✅ ALREADY INTEGRATED (8)
| Connector | Status | Notes |
|-----------|--------|-------|
| Stripe | ✅ Full | `/api/payments.py` - Checkout, subscriptions, webhooks |
| Resend | ✅ Full | `/api/email_service.py` - Graceful fallback to console |
| ElevenLabs | ✅ Full | `/api/voice.py` - Text-to-speech synthesis |
| Anthropic Claude | ✅ Full | `/api/ws.py` - Persona chat (claude-sonnet-4-6) |
| GitHub OAuth2 | ✅ Full | `/api/routers/advanced_auth.py` |
| Google OAuth2 | ✅ Full | `/api/routers/advanced_auth.py` |
| Redis | ✅ Opt | `/api/cache.py` - Session/request caching (graceful degradation) |
| PostgreSQL | ✅ Full | `/api/db.py` - Primary data store with soft deletes |

---

## 🔴 TIER 1: CRITICAL (Launch Blockers)

### 1. Error Tracking - SENTRY
**Why:** Catch production bugs before users report them

**Setup:** 30 minutes
```python
# Step 1: Add to requirements.txt
sentry-sdk[fastapi]>=1.40.0

# Step 2: Add to api/main.py startup
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)

# Step 3: Add SENTRY_DSN to Vercel secrets
# https://sentry.io → Create project → Copy DSN

# Step 4: Test
# Trigger error: raise Exception("Test error")
```

**Alternatives:** Datadog ($0.05/min), NewRelic (free tier)
**Recommendation:** Sentry (best Python support, free tier 10k events/month)

---

### 2. Analytics - POSTHOG
**Why:** Track user behavior for product decisions

**Setup:** 1 hour
```python
# Step 1: Add to requirements.txt
posthog>=3.0.0

# Step 2: Initialize in api/main.py
from posthog import Posthog
posthog = Posthog(
    api_key=os.getenv("POSTHOG_API_KEY"),
    host="https://eu.posthog.com"  # GDPR-compliant EU server
)

# Step 3: Add event tracking to endpoints
# In checkout endpoint:
posthog.capture(
    distinct_id=user.id,
    event="checkout_completed",
    properties={
        "persona_id": persona_id,
        "amount_cents": amount,
        "tier": tier,
    }
)

# Step 4: Create dashboard for:
# - Daily active users
# - Checkout completion rate
# - Revenue per user
# - Feature adoption rates
```

**Key Events to Track:**
```
1. User signup (signup_complete)
2. Email verified (email_verified)
3. Persona purchased (persona_purchased)
4. Checkout started (checkout_started)
5. Checkout completed (checkout_completed)
6. Subscription renewed (subscription_renewed)
7. Chat message sent (chat_message)
7. Error occurred (error_logged)
```

**Alternatives:** Segment, Mixpanel, Amplitude
**Recommendation:** PostHog (GDPR-compliant, self-hosted option, best for startups)

---

### 3. File Storage - SUPABASE STORAGE
**Why:** User avatars, persona images, backups

**Setup:** 2 hours
```python
# Step 1: Enable in Supabase dashboard
# Dashboard → Storage → Create new bucket: "persona-avatars"

# Step 2: Create api/storage.py
from supabase import create_client, Client

class StorageManager:
    def __init__(self):
        self.client: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
    
    async def upload_avatar(self, user_id: str, file_data: bytes):
        path = f"{user_id}/avatar.jpg"
        response = self.client.storage \
            .from_("persona-avatars") \
            .upload(path, file_data)
        return response
    
    async def get_download_url(self, user_id: str):
        url = self.client.storage \
            .from_("persona-avatars") \
            .get_public_url(f"{user_id}/avatar.jpg")
        return url

# Step 3: Add endpoint to api/main.py
@app.post("/me/avatar")
async def upload_avatar(
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    storage = StorageManager()
    file_data = await file.read()
    await storage.upload_avatar(user.id, file_data)
    return {"url": await storage.get_download_url(user.id)}

# Step 4: Add to requirements.txt
python-multipart>=0.0.9
supabase>=2.0.0
```

**Alternatives:** AWS S3 ($0.023/GB), Vercel Blob ($0.5/GB), Cloudinary
**Recommendation:** Supabase Storage (already using Supabase, 1GB free, simplest)

---

### 4. Secrets Management - VERCEL SECRETS
**Why:** Keep API keys secure, rotate without redeploy

**Setup:** 30 minutes
```bash
# Add to Vercel dashboard under Settings → Environment Variables

# Critical
SENTRY_DSN=https://key@sentry.io/project
POSTHOG_API_KEY=phc_xxxxx
SUPABASE_SERVICE_ROLE_KEY=eyJxxx

# Important
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
ANTHROPIC_API_KEY=sk-ant-xxx
ELEVENLABS_API_KEY=sk_xxx
RESEND_API_KEY=re_xxx

# Optional
REDIS_URL=redis://...
DATABASE_URL=postgresql://...
```

**No code changes needed** - Vercel automatically injects env vars

**Alternatives:** AWS Secrets Manager, HashiCorp Vault
**Recommendation:** Vercel Secrets (already integrated, easiest)

---

### 5. Email Templates - RESEND UPGRADE
**Why:** Professional signup/password-reset/receipt emails

**Setup:** 1 hour
```python
# Already using Resend in api/email_service.py
# Just add templates:

from resend import Resend

client = Resend(api_key=os.getenv("RESEND_API_KEY"))

async def send_signup_email(email: str, verification_code: str):
    """Send email verification link on signup"""
    response = client.emails.send(
        {
            "from": os.getenv("FROM_EMAIL"),
            "to": email,
            "subject": "Welcome to Persona Hub! Verify your email",
            "html": f"""
            <h1>Welcome to Persona Hub</h1>
            <p>Click the link to verify your email:</p>
            <a href="https://yourdomain.com/verify?code={verification_code}">
                Verify Email
            </a>
            <p>Or copy: {verification_code}</p>
            """,
        }
    )
    return response

async def send_password_reset_email(email: str, reset_token: str):
    """Send password reset link"""
    response = client.emails.send(
        {
            "from": os.getenv("FROM_EMAIL"),
            "to": email,
            "subject": "Reset your Persona Hub password",
            "html": f"""
            <h1>Password Reset</h1>
            <p><a href="https://yourdomain.com/reset?token={reset_token}">
                Reset Password
            </a></p>
            """,
        }
    )
    return response

async def send_receipt_email(email: str, persona_id: str, amount: int):
    """Send purchase receipt"""
    response = client.emails.send(
        {
            "from": os.getenv("FROM_EMAIL"),
            "to": email,
            "subject": f"Receipt: {persona_id} purchase",
            "html": f"""
            <h1>Purchase Confirmation</h1>
            <p>You've purchased <strong>{persona_id}</strong></p>
            <p>Amount: ${amount/100:.2f}</p>
            <p>Receipt ID: {uuid.uuid4()}</p>
            """,
        }
    )
    return response
```

**Add to endpoints:**
```python
@app.post("/auth/register")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # Create user...
    user = User(email=data.email, ...)
    db.add(user)
    db.commit()
    
    # Send verification email
    verification_code = generate_code()
    await send_signup_email(user.email, verification_code)
    
    return {"message": "Check your email to verify"}

@app.post("/checkout/{persona_id}")
async def checkout(...):
    # Create Stripe session...
    
    # Send receipt email
    await send_receipt_email(user.email, persona_id, amount)
    
    return {"checkout_url": session.url}
```

**Alternatives:** SendGrid, Mailgun, AWS SES
**Recommendation:** Resend (already integrated, simplest)

---

## 🟡 TIER 2: IMPORTANT (Week 1)

| Connector | Purpose | Time | Priority |
|-----------|---------|------|----------|
| **Background Jobs** | Async email, cleanup | 4h | HIGH |
| **Monitoring Dashboard** | Prometheus/Grafana metrics | 3h | MEDIUM |
| **Search** | Elasticsearch for persona search | 5h | MEDIUM |
| **GDPR Endpoints** | Data export/deletion | 3h | HIGH |
| **Log Aggregation** | Datadog/LogRocket/ELK | 2h | MEDIUM |

### Implementation Order Week 1:
1. Monday: Background jobs (Bull + Redis)
2. Wednesday: GDPR endpoints (/api/account/export, /api/account/delete)
3. Friday: Monitoring dashboard setup

---

## 🟢 TIER 3: NICE-TO-HAVE (Post-Launch)

| Connector | Use Case | Time |
|-----------|----------|------|
| **Feature Flags** | A/B testing, gradual rollouts | 2h |
| **CDN** | Fast image delivery | 1h |
| **Load Testing** | k6/Artillery scripts | 2h |
| **SMS** | 2FA, notifications | 2h |
| **Webhooks** | Make.com/Zapier automations | 3h |
| **Secondary Payments** | PayPal backup | 4h |

---

## LAUNCH TIMELINE

### Day 1 (5 hours)
```
08:00 - Sentry setup              (30 min)
09:00 - PostHog analytics         (1h)
10:30 - AWS/Vercel Secrets        (30 min)
12:00 - Email templates           (1h)
13:30 - Supabase Storage          (1.5h)
15:00 - Testing + Deploy
```

### Day 2-3
```
Background Jobs (Bull + Redis)
Monitoring Dashboard
GDPR Compliance Endpoints
Log Aggregation
```

### Week 1
```
Search Indexing (Elasticsearch)
Custom Alerts
Load Testing
Performance Tuning
```

---

## SETUP CHECKLIST

### Sentry
- [ ] Create Sentry account
- [ ] Create project (Python/FastAPI)
- [ ] Copy DSN
- [ ] Add SENTRY_DSN to Vercel
- [ ] Test error tracking
- [ ] Configure alert rules

### PostHog
- [ ] Create PostHog account (EU data center)
- [ ] Get API key
- [ ] Add POSTHOG_API_KEY to Vercel
- [ ] Implement event tracking (6 key events)
- [ ] Create dashboard
- [ ] Set up alerts

### Supabase Storage
- [ ] Create bucket "persona-avatars"
- [ ] Set storage rules (authenticated users only)
- [ ] Get SERVICE_ROLE_KEY
- [ ] Add SUPABASE_SERVICE_ROLE_KEY to Vercel
- [ ] Implement upload endpoint
- [ ] Test file upload/download

### Email Templates
- [ ] Verify Resend domain
- [ ] Set FROM_EMAIL env var
- [ ] Implement 3 email templates
- [ ] Test signup email
- [ ] Test reset email
- [ ] Test receipt email

### Vercel Secrets
- [ ] Add all env vars to Vercel dashboard
- [ ] Verify CI/CD picks up env vars
- [ ] Test production deployment
- [ ] Verify secrets don't leak in logs

---

## PRODUCTION READINESS

After Tier 1 setup:
- ✅ Errors tracked in Sentry
- ✅ Analytics visible in PostHog
- ✅ Files stored in Supabase
- ✅ Emails sent via Resend
- ✅ Secrets secure in Vercel
- ✅ Ready for staging deployment

---

## COST BREAKDOWN (Monthly)

| Service | Free Tier | Paid | Recommended |
|---------|-----------|------|-------------|
| **Sentry** | 10k events | $0.05/event | Free (start) |
| **PostHog** | 1M events | $0/month EU | Free |
| **Supabase Storage** | 1 GB | $0.025/GB | Free (1GB) |
| **Resend** | 100/day | $0 included | Free |
| **Vercel** | 100GB bandwidth | $0 | Free |
| **Redis** | - | $5+ | Optional (start without) |
| **Stripe** | - | 2.9% + $0.30 | $X/month |
| **Total First Month** | ~$0 | - | **$0** |

---

## VERIFICATION AFTER SETUP

```bash
# Test Sentry
curl http://localhost:8000/test-error

# Test PostHog
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# Test file upload
curl -X POST http://localhost:8000/me/avatar \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@avatar.jpg"

# Test email
# Check inbox for verification email

# Production test (after deploy to Vercel)
curl https://your-domain.com/health
```

---

## SUMMARY TABLE

| Component | Status | Effort | Timeline |
|-----------|--------|--------|----------|
| Error Tracking (Sentry) | ⏳ Todo | 30 min | Day 1 |
| Analytics (PostHog) | ⏳ Todo | 1h | Day 1 |
| File Storage (Supabase) | ⏳ Todo | 2h | Day 1 |
| Email Templates (Resend) | ⏳ Todo | 1h | Day 1 |
| Secrets (Vercel) | ⏳ Todo | 30 min | Day 1 |
| **TIER 1 TOTAL** | - | **5h** | **Day 1** |
| Background Jobs | ⏳ Todo | 4h | Week 1 |
| Monitoring | ⏳ Todo | 3h | Week 1 |
| Search | ⏳ Todo | 5h | Week 1 |
| GDPR Endpoints | ⏳ Todo | 3h | Week 1 |
| Log Aggregation | ⏳ Todo | 2h | Week 1 |

---

## Next Steps

1. ✅ Review this roadmap
2. ⏳ Day 1: Implement Tier 1 (5 hours)
3. ⏳ Day 2-3: Deploy to staging
4. ⏳ Week 1: Implement Tier 2
5. ⏳ Week 2: Launch to production

**Estimated Time to Production: 3-4 days**

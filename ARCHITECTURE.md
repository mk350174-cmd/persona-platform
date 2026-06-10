# Persona Platform Architecture

**Version:** 1.0.0  
**Last Updated:** June 2024  
**Audience:** Developers, DevOps, Architects

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagram](#architecture-diagram)
4. [Core Components](#core-components)
5. [Data Model](#data-model)
6. [Authentication & Security](#authentication--security)
7. [Payment Processing](#payment-processing)
8. [Compilation Pipeline](#compilation-pipeline)
9. [Deployment Architecture](#deployment-architecture)
10. [Scalability & Performance](#scalability--performance)
11. [Disaster Recovery](#disaster-recovery)

---

## System Overview

**Persona Platform** is a **SaaS application** enabling users to:
- Browse and purchase AI personas (495 trained models)
- Chat with personas via WebSocket
- Compile personas for deployment (PyTorch, ONNX, etc.)
- Manage subscriptions and billing (Stripe integration)
- Generate voice synthesis (ElevenLabs API)

**Core Characteristics:**
- **Public API** (REST + WebSocket)
- **Multi-tenant** (user isolation via API keys)
- **Stateless** (horizontal scaling ready)
- **Event-driven** (Stripe webhooks, async compilation)
- **GDPR/KVKK compliant** (soft delete, audit logs)

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI (Python 3.11) | REST + WebSocket endpoints |
| **Web Framework** | Starlette | Request/response handling |
| **Database** | PostgreSQL 13+ | Primary data store |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Authentication** | JWT (API Key format) | Request authentication |
| **Password Hashing** | Argon2 | Secure password storage |
| **API Key Hashing** | SHA-256 | Secure key storage |
| **Email Verification** | Resend API | Email delivery |
| **Payments** | Stripe API | Billing, subscriptions, invoices |
| **Voice Generation** | ElevenLabs API | Text-to-speech synthesis |
| **WebSocket** | WebSockets/asyncio | Real-time chat |
| **Rate Limiting** | Redis (optional) | Request throttling |
| **Migrations** | Alembic | Database versioning |
| **Testing** | pytest | Unit & integration tests |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Container** | Docker | Deployment packaging |
| **Reverse Proxy** | Nginx | TLS, rate limiting, compression |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web App    │  │  Mobile App  │  │  CLI Tool    │          │
│  │  (React)     │  │  (iOS/Android)  │  (Python SDK)          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                           │
                   (HTTPS/WSS)
                           │
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                             │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Nginx (TLS 1.2+, rate limiting, compression, logging)  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                      (HTTP)
                           │
┌─────────────────────────────────────────────────────────────────┐
│                   API Server Layer                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  FastAPI Application                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Auth Router  │  │Payment Router│  │ Compile      │   │ │
│  │  │ - Register   │  │ - Checkout   │  │ Router       │   │ │
│  │  │ - Login      │  │ - Subscribe  │  │ - Compile    │   │ │
│  │  │ - Verify     │  │ - Billing    │  │ - Voice Gen  │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │ Middleware Stack                                  │   │ │
│  │  │ - Auth (API key extraction & validation)         │   │ │
│  │  │ - Security Headers (CSP, CORS, etc.)            │   │ │
│  │  │ - Rate Limiting (per-key + per-endpoint)        │   │ │
│  │  │ - Audit Logging (security events)               │   │ │
│  │  │ - CORS (cross-origin requests)                  │   │ │
│  │  │ - Request ID (tracing)                          │   │ │
│  │  └──────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
      │                    │                    │
      │                    │                    │
  (SQL)             (HTTP to external APIs)  (WS)
      │                    │                    │
┌─────────────────────────────────────────────────────────────────┐
│                  Integration Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Stripe API       │  │ Resend Email API │  │ ElevenLabs   │ │
│  │ - Checkout       │  │ - Verification   │  │ - Voice Gen  │ │
│  │ - Billing        │  │ - Notifications  │  │ - Synthesis  │ │
│  │ - Invoices       │  │                  │  │              │ │
│  │ - Webhooks       │  │                  │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
      │
   (SQL over TCP)
      │
┌─────────────────────────────────────────────────────────────────┐
│              Data Persistence Layer                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PostgreSQL Database                                       │  │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │ │  User    │ │ Purchase │ │Invoice   │ │RateLimitUsage│ │  │
│  │ │  Tables  │ │ & Sub    │ │ & Wallet │ │ & AuditLog   │ │  │
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │  │
│  │ Indexes: 20+, Connection Pool: 20, Max Overflow: 10     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
      │
   (Backup)
      │
┌─────────────────────────────────────────────────────────────────┐
│              Backup & Replication                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PostgreSQL Streaming Replication (standby node)          │  │
│  │ + Daily S3 backups (via pg_dump)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. API Server (FastAPI)

**File:** `api/main.py`

**Responsibilities:**
- Route HTTP/WebSocket requests
- Apply middleware (auth, security, rate limiting, audit)
- Invoke business logic
- Return JSON responses

**Key Endpoints:**
- `GET /health` — Health checks (public)
- `GET /personas` — Browse catalog (public)
- `POST /auth/register` — User registration (public)
- `POST /auth/login` — Email/password auth (public)
- `POST /checkout/*` — Stripe checkouts (authenticated)
- `POST /v1/compile/*` — Model compilation (authenticated)
- `WebSocket /ws/chat/*` — Real-time chat (authenticated)

**Startup Flow:**
1. Load environment variables
2. Initialize database connection pool
3. Run pending Alembic migrations
4. Register middleware stack
5. Load persona metadata (495 personas)
6. Listen on port 8000

---

### 2. Database Layer (SQLAlchemy + PostgreSQL)

**File:** `api/db.py`

**Core Models:**

| Model | Purpose | Key Fields |
|-------|---------|-----------|
| `User` | User accounts | `id`, `email`, `password_hash`, `api_key_hash`, `stripe_customer_id`, `deleted_at` |
| `EmailVerificationToken` | Email verification | `token`, `user_id`, `expires_at` |
| `LoginAttempt` | Brute force tracking | `user_id`, `ip_address`, `success`, `timestamp` |
| `Persona` | AI persona metadata | `id`, `name`, `tier`, `voice_id`, `image_url` |
| `Purchase` | Single persona purchases | `id`, `user_id`, `persona_id`, `created_at`, `deleted_at` |
| `Subscription` | Recurring subscriptions | `id`, `user_id`, `tier`, `status`, `current_period_start`, `deleted_at` |
| `Invoice` | Payment records | `id`, `user_id`, `stripe_invoice_id`, `amount`, `status` |
| `Wallet` | User credit balance | `id`, `user_id`, `balance`, `currency` |
| `ReferralCode` | Referral tracking | `code`, `user_id`, `created_at` |
| `ReferralCredit` | Referral rewards | `id`, `issuer_id`, `recipient_id`, `amount` |
| `PromoCode` | Discount codes | `code`, `discount_percent`, `expires_at` |
| `StripeEvent` | Webhook idempotency | `stripe_event_id`, `processed_at` |
| `AuditLog` | Security event log | `user_id`, `event_type`, `details`, `timestamp` |

**Indexes:** 20+ composite indexes on:
- `users(deleted_at, email)`
- `purchases(user_id, persona_id)`
- `subscriptions(user_id, status)`
- `audit_log(user_id, timestamp)`
- `login_attempts(user_id, ip_address, timestamp)`

**Connection Pool:**
- Pool size: 20 connections
- Max overflow: 10 overflow connections
- Idle timeout: 3600 seconds

---

### 3. Authentication Service (api/auth.py)

**Responsibilities:**
- Password hashing (Argon2)
- API key hashing (SHA-256 prefix-based)
- Failed login attempt tracking
- User enumeration prevention
- Constant-time password comparison

**Key Functions:**
```python
def hash_password(password: str) -> str
def verify_password(password: str, hash: str) -> bool

def hash_api_key(api_key: str) -> tuple[str, str]  # (prefix, hash)
def verify_api_key(api_key: str, stored_hash: str) -> bool

def check_lockout(db: Session, user_id: str) -> bool
def record_failed_attempt(db: Session, user_id: str, ip: str)
def clear_failed_attempts(db: Session, user_id: str)
```

**Lockout Policy:**
- 5 consecutive failed login attempts
- 5-minute lockout window per IP + user combo
- Clears on successful login

---

### 4. Payment Processing (api/payments.py)

**Integration:** Stripe API

**Responsibilities:**
- Create checkout sessions
- Process webhooks
- Manage subscriptions
- Handle refunds
- Multi-currency support

**Key Flows:**

**Checkout Flow:**
```
1. User calls POST /checkout/{persona_id}
2. Check wallet balance
3. Deduct available credits
4. Create Stripe session (remaining amount)
5. Return checkout URL
6. User completes payment via Stripe UI
7. Stripe webhook fires → persona access granted
```

**Webhook Flow:**
```
1. Stripe sends POST /webhook/stripe
2. Verify signature with STRIPE_WEBHOOK_SECRET
3. Check StripeEvent table (idempotency)
4. Process event:
   - checkout.session.completed → grant access
   - invoice.payment_succeeded → record invoice
   - customer.subscription.deleted → revoke access
5. Return 200 OK
```

**Currency Conversion:**
```python
def locale_to_currency(locale: str) -> str
# "en-US" → "USD"
# "de-DE" → "EUR"
# "tr-TR" → "TRY"

def get_localized_price(base_price_usd: float, currency: str) -> float
# Fetch exchange rates, apply conversion
# Cache rates for 1 hour
```

---

### 5. Email Service (api/email_service.py)

**Integration:** Resend API

**Responsibilities:**
- Send verification emails
- Email templates
- Retry logic
- Dev mode (stdout fallback)

**Verification Flow:**
```
1. User calls POST /auth/request-verification
2. Generate 24-hour token (EmailVerificationToken)
3. Send email via Resend:
   "Click here to verify: {BASE_URL}/verify?token={token}"
4. User clicks link
5. POST /auth/verify-email with token
6. Update user.email_verified = true
```

---

### 6. Rate Limiting Middleware (api/middleware/rate_limiter.py)

**Strategy:** Per-API-key + per-endpoint

**Configuration:**
```python
RATE_LIMITS = {
    "GET:/personas": 1000,  # 1000 requests/hour
    "POST:/v1/compile": 100,  # 100 requests/hour
    "POST:/checkout": 50,     # 50 requests/hour
}
```

**Implementation:**
- Extract API key from `X-API-Key` header
- Track usage per `(api_key, endpoint)` tuple
- Hourly reset windows (aligned to UTC)
- In-memory storage (can scale to Redis)

**Response Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1623336000
```

---

### 7. Audit Logging (api/middleware/audit_logger.py)

**Responsibilities:**
- Log security-relevant events
- Dual-write: database + application logs
- Include user, IP, action, timestamp
- GDPR-compliant (soft delete support)

**Logged Events:**
| Event | Details |
|-------|---------|
| `USER_REGISTERED` | Email, IP |
| `USER_LOGGED_IN` | User ID, IP |
| `LOGIN_FAILED` | User ID, IP, reason |
| `PASSWORD_CHANGED` | User ID, IP |
| `API_KEY_GENERATED` | User ID, key prefix |
| `API_KEY_REVOKED` | User ID, key prefix |
| `PERSONA_PURCHASED` | User ID, persona ID, amount |
| `SUBSCRIPTION_CREATED` | User ID, tier, amount |
| `REFUND_ISSUED` | Admin ID, purchase ID, amount |

---

### 8. Compilation Pipeline (api/routers/compile.py)

**Responsibilities:**
- Verify user owns persona
- Trigger model compilation
- Generate download URLs
- Track compilation status

**Flow:**
```
1. User calls POST /v1/compile/{persona_id}
2. Verify user purchased persona
3. Check compilation tier (basic/pro/expert)
4. Trigger async compilation job
5. Return download URL + checksum
6. Download link expires in 7 days
7. User can re-compile anytime
```

---

## Data Model

### User Entity Relationship

```
User (1) ←→ (N) Purchase
  │           └─ persona_id → Persona
  │
  ├─→ (1) Subscription
  │       └─ tier (basic_monthly/pro_annual/etc.)
  │
  ├─→ (1) Wallet
  │       ├─ (N) ReferralCredit (as issuer)
  │       └─ (N) ReferralCredit (as recipient)
  │
  ├─→ (1) ReferralCode
  │       └─ code (unique per user)
  │
  ├─→ (N) Invoice
  │       ├─ stripe_invoice_id (Stripe reference)
  │       └─ amount, currency, status
  │
  ├─→ (N) LoginAttempt
  │       └─ ip_address, success flag
  │
  └─→ (N) AuditLog
          └─ event_type, details, timestamp
```

### Purchase & Access Control

```
User X purchases Persona Y:
1. Create Purchase(user_id=X, persona_id=Y)
2. Record Invoice with Stripe details
3. Create ReferralCredit if referred
4. Update User.purchases (many-to-many)

User X can compile Persona Y if:
- exists Purchase(user_id=X, persona_id=Y)
- deleted_at is NULL
- Purchase created_at < current time
```

---

## Authentication & Security

### API Key Authentication

**Format:**
```
Header: X-API-Key: prs_abc123def456...
```

**Storage:**
```python
# Database stores:
api_key_prefix = "prs_"  # First 4 chars
api_key_hash = sha256("prs_abc123def456...")  # SHA-256

# Lookup:
# Given "prs_abc123def456..." from request:
# 1. Extract prefix "prs_"
# 2. Find User where api_key_prefix = "prs_"
# 3. Verify hash matches
```

**Rotation Grace Period:** 7 days
- Old key remains valid during grace period
- New key issued immediately
- Both keys can be used until period expires

### Password Security

**Hashing:** Argon2 (Memory-hard function)
```python
# Register:
password_hash = argon2.hash(password)  # ~150ms per hash
user.password_hash = password_hash

# Login:
if argon2.verify(password, user.password_hash):
    clear_failed_attempts()
else:
    record_failed_attempt()
```

**Failed Login Lockout:**
```
Attempt 1: Success → Clear counter
Attempt 1: Fail → Counter = 1
Attempt 2: Fail → Counter = 2
...
Attempt 5: Fail → Counter = 5, Lockout = now + 5 minutes
Attempt 6: → Return 429 "Account locked"
```

### CORS (Cross-Origin Resource Sharing)

**Configuration:**
```python
CORS_ORIGINS = [
    "https://persona-hub.com",
    "https://www.persona-hub.com",
    "http://localhost:3000",  # Dev only
]

# Allowed methods: GET, POST, DELETE
# Allowed headers: Content-Type, X-API-Key
# Allow credentials: true
# Max age: 3600s
```

### Content Security Policy (CSP)

**Headers:**
```
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'nonce-{random}';
  style-src 'self' 'unsafe-inline';
  img-src 'self' https:;
  connect-src 'self' https://api.stripe.com https://checkout.stripe.com
```

**Nonce Generation:** Random per request, prevents inline script injection

---

## Payment Processing

### Subscription Tiers

| Tier | Price | Billing | Personas | Features |
|------|-------|---------|----------|----------|
| Basic (Monthly) | $19.99 | Monthly | 10 | Chat, compile, voice |
| Pro (Monthly) | $49.99 | Monthly | 100 | Chat, compile, voice, priority |
| Basic (Annual) | $99.00 | Annual | 10 | **20% off** |
| Pro (Annual) | $290.00 | Annual | 100 | **20% off** |

### Promo Code System

```python
# Create promo code (admin only):
code = "SAVE20"
discount = 20  # percent
expires_at = datetime(2024, 12, 31)

# Apply at checkout:
POST /checkout/einstein?promo=SAVE20
→ price = 19.99 * (1 - 0.20) = $15.99

# Track usage:
PromoCode.times_used += 1
PromoCode.last_used = now
```

### Wallet & Credit System

```
User balance tracking:
1. User registers → Wallet created with balance = 0
2. Referral credit earned → balance += 5.00
3. Manual admin credit → balance += X.00
4. Checkout → Check balance
   - If balance >= total: Deduct full amount, no Stripe charge
   - If balance < total: Deduct balance, charge (total - balance) to Stripe
   - If balance = 0: Charge full amount to Stripe

Example:
- balance = 50.00
- persona cost = 19.99
- Stripe charges: 19.99 - 50.00 = 0 (wallet covers it)
- balance becomes: 50.00 - 19.99 = 30.01
```

### Referral Program

```
Flow:
1. User A calls POST /me/referral-code
   → Returns code = "REF_abc123"
   
2. User B registers, mentions code "REF_abc123"
   
3. User B makes first purchase:
   → Stripe webhook fires
   → Check PromoCode table for "REF_abc123"
   → If issuer is User A:
     - Add ReferralCredit(issuer=A, recipient=B, amount=5.00)
     - Update Wallet(user_id=A).balance += 5.00
   
4. User A can immediately use balance for next purchase
```

---

## Compilation Pipeline

### Supported Formats

| Format | Size | Use Case | Hardware |
|--------|------|----------|----------|
| PyTorch | 450 MB | Development, research | CPU/GPU |
| ONNX | 400 MB | Production inference | CPU/GPU/TPU |
| Safetensors | 380 MB | Secure, fast loading | CPU/GPU |
| TensorFlow | 500 MB | TensorFlow ecosystem | TPU/GPU |

### Compilation Tiers

| Tier | Parameters | Size | Latency | Cost |
|------|-----------|------|---------|------|
| Basic | 26M | 120 MB | ~2s | Included |
| Pro | 26M + weights | 450 MB | <1s | +$5 |
| Expert | Full precision | 1.2 GB | <500ms | +$15 |

### Multi-Platform Support

```
POST /v1/compile/{persona_id}/all-platforms
→ Generates:
  - iOS: .xcframework (arm64)
  - Android: .aar (arm64-v8a)
  - Web: .js (WASM+onnx.js)
  - Desktop: .so/.dll/.dylib
```

---

## Deployment Architecture

### Production Environment

```
┌─────────────────────────────────────────────────────────────┐
│  AWS ECS Cluster (Elastic Container Service)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Task Definition (Docker)                             │   │
│  │ - Image: ghcr.io/mk350174-cmd/persona-platform      │   │
│  │ - CPU: 2 vCPU                                        │   │
│  │ - Memory: 4 GB                                       │   │
│  │ - Port: 8000                                         │   │
│  │ - Environment: Prod secrets from AWS Secrets Manager│   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Auto-Scaling Group                                   │   │
│  │ - Min: 2 instances (HA)                             │   │
│  │ - Target: 5 instances (peak)                        │   │
│  │ - Max: 10 instances (burst)                         │   │
│  │ - Metric: CPU > 70%, Memory > 80%                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                │
    ┌────┴────┬───────────┴────┐
    │         │                │
┌───┴─┐   ┌──┴──┐          ┌──┴──┐
│ ALB │   │ NLB  │          │ECS #3
│     │   │      │          │     
└─────┘   └──────┘          └─────┘
   (TLS)   (UDP)
    │         │
    └─────────┼──────────────────┐
              │                  │
         ┌────┴────┐         ┌───┴───┐
         │CloudFlare│        │Route53│
         │CDN       │        │DNS    │
         └──────────┘        └───────┘
```

### Database Setup

```
Primary: PostgreSQL 13+
- Master node (write operations)
- Streaming replication to standby
- Daily automated backups to S3
- Restore time: ~30 minutes
- RPO (Recovery Point Objective): 1 hour
```

### Docker Deployment

```dockerfile
# Multi-stage build
FROM python:3.11-slim as base
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc postgresql-client

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations on startup
CMD ["sh", "-c", "alembic upgrade head && \
    uvicorn api.main:app --host 0.0.0.0 --port 8000"]
```

---

## Scalability & Performance

### Horizontal Scaling

**Stateless Design:** Each instance is independent
```
Request Load Balancing:
├─ Instance 1 (v1.2.3)
├─ Instance 2 (v1.2.3)
├─ Instance 3 (v1.2.3)
└─ Instance 4 (v1.2.3)

Load balancer distributes requests equally.
Session affinity NOT required.
```

### Database Optimization

**20+ Indexes:**
```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key_prefix ON users(api_key_prefix);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);

-- Purchase queries
CREATE INDEX idx_purchases_user_id ON purchases(user_id);
CREATE INDEX idx_purchases_persona_id ON purchases(persona_id);
CREATE INDEX idx_purchases_user_persona ON purchases(user_id, persona_id);

-- Audit trail
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id, timestamp);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);

-- Rate limiting
CREATE INDEX idx_rate_limit_usage_key_endpoint ON rate_limit_usage(api_key, endpoint, window_start);
```

### Caching Strategy

```python
# Cache personnel for 1 hour
@cache(expire=3600)
def get_personas():
    return db.query(Persona).all()

# Cache subscription tiers (rarely change)
@cache(expire=86400)
def get_subscription_tiers():
    return SUBSCRIPTION_TIERS

# Cache exchange rates for 1 hour
@cache(expire=3600)
def get_exchange_rates():
    return fetch_from_external_api()

# Rate limit state (memory or Redis)
# Per-key + per-endpoint lookups (O(1))
```

### Performance Targets

| Metric | Target | Mechanism |
|--------|--------|-----------|
| API Response | <200ms p95 | Database indexes, caching |
| WebSocket Latency | <100ms p95 | Async I/O, connection pooling |
| Compilation Time | <30s p50 | Pre-built models, CDN |
| Checkout Flow | <5s p95 | Stripe API optimization |
| Login | <500ms p95 | Argon2 parameters tuned |

---

## Disaster Recovery

### Backup Strategy

```
Type:                Frequency:           Storage:
─────────────────────────────────────────────────────
Automated snapshots  Every 6 hours        AWS EBS
Database backups     Daily (11 PM UTC)    S3 (encrypted)
WAL (point-in-time)  Continuous           S3 (continuous replication)
Cold backup          Monthly              Glacier (7-year retention)
```

### Recovery Procedures

**Database Restore (< 1 hour):**
1. Stop all API instances
2. Restore database from backup
3. Run migrations: `alembic upgrade head`
4. Verify integrity: `SELECT COUNT(*) FROM user` (matches baseline)
5. Restart API instances
6. Health check: Verify /health endpoint

**Full System Failover (< 30 minutes):**
1. Update Route 53 to secondary region
2. Trigger CloudFormation stack in standby region
3. Restore database to standby
4. Redirect traffic through failover ALB
5. Verify all services operational

### Uptime SLA

```
Target: 99.9% uptime (43 minutes/month downtime)

Mechanisms:
├─ Multi-AZ deployment (3 availability zones)
├─ Auto-scaling (handles 2x traffic)
├─ Health checks (60-second detection)
├─ Circuit breaker pattern (external API failures)
└─ Graceful degradation (reduced features vs. full outage)

Monitored by: CloudWatch, PagerDuty, Datadog
```

---

## Development Workflow

### Local Development

```bash
# 1. Clone & setup
git clone https://github.com/mk350174-cmd/persona-platform.git
cd persona-platform
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-api.txt

# 2. Environment
cp .env.example .env
# Edit DATABASE_URL=sqlite:///./persona.db (local dev)

# 3. Database
alembic upgrade head

# 4. Run server
uvicorn api.main:app --reload --port 8000

# 5. Test
pytest tests/ --cov=api
```

### CI/CD Pipeline

```
On git push:
├─ GitHub Actions triggered
├─ Multi-Python matrix (3.9, 3.10, 3.11, 3.12)
├─ Run tests: pytest (75% coverage minimum)
├─ Security: gitleaks, bandit, safety
├─ Quality: flake8, mypy, black, isort
├─ Build Docker image
├─ Push to ghcr.io
└─ Deploy to production (if main branch)
```

### Release Process

```
1. Create tag: git tag -a v1.2.3
2. Push tag: git push origin v1.2.3
3. GitHub Actions:
   ├─ Build Docker image
   ├─ Push with tag v1.2.3
   ├─ Create GitHub Release
   └─ Generate changelog
4. Manual deployment window (requires approval)
5. Health checks post-deploy
6. Slack notification to #deployments
```

---

## Monitoring & Observability

### Key Metrics

```
Application:
├─ Requests/sec
├─ Error rate (5xx errors)
├─ Response latency (p50, p95, p99)
├─ Active WebSocket connections
└─ API key cache hit rate

Database:
├─ Query latency
├─ Connection pool utilization
├─ Replication lag
└─ Disk usage

Business:
├─ Active users
├─ Revenue (MRR, ARR)
├─ Subscription churn
└─ Compilation jobs/hour
```

### Alerting

```
Critical (PagerDuty):
├─ Error rate > 5%
├─ Response latency p95 > 5s
├─ Database replication lag > 10s
└─ API availability < 99%

Warning (Slack #alerts):
├─ Error rate > 1%
├─ Response latency p95 > 1s
└─ Disk usage > 80%
```

---

## Future Improvements (H90+)

- [ ] Canary deployments (10% traffic ramp)
- [ ] A/B testing framework
- [ ] Automatic rollback on error rate spike
- [ ] Performance regression detection
- [ ] Distributed tracing (Jaeger/Zipkin)
- [ ] Metrics aggregation (Prometheus)
- [ ] Advanced rate limiting (token bucket)
- [ ] Redis cluster for caching/sessions
- [ ] Database sharding (multi-tenant isolation)
- [ ] GraphQL API (in addition to REST)

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Stripe API](https://stripe.com/docs/api)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/sql-explain.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [AWS ECS](https://aws.amazon.com/ecs/)

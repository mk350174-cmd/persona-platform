# Persona Platform

**AI-powered personas as a service** — Compile, chat with, and monetize 495 trained AI personas.

[![CI Status](https://github.com/mk350174-cmd/persona-platform/actions/workflows/ci-matrix.yml/badge.svg)](https://github.com/mk350174-cmd/persona-platform/actions)
[![Test Coverage](https://codecov.io/gh/mk350174-cmd/persona-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/mk350174-cmd/persona-platform)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen)](https://github.com/mk350174-cmd/persona-platform)

---

## Overview

Persona Platform is a **production-ready SaaS backend** enabling users to:

- **Browse** 495 AI personas (scientists, philosophers, historical figures)
- **Purchase** lifetime access or subscription plans
- **Compile** personas into multiple formats (PyTorch, ONNX, Safetensors)
- **Chat** with personas via WebSocket (real-time conversations)
- **Generate** voice synthesis (ElevenLabs integration)
- **Manage** subscriptions and billing (Stripe integration)

**Production Grade:**
- ✅ FastAPI backend with async/await
- ✅ PostgreSQL with 20+ indexes
- ✅ Stripe payment integration
- ✅ Multi-Python testing (3.9–3.12)
- ✅ CI/CD automation (GitHub Actions)
- ✅ Security hardening (auth, rate limiting, audit logs)
- ✅ GDPR/KVKK compliance (soft delete)
- ✅ 75%+ test coverage

---

## Quick Start

### Development (Local SQLite)

```bash
# Clone repository
git clone https://github.com/mk350174-cmd/persona-platform.git
cd persona-platform

# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements-api.txt

# Configure environment
cp .env.example .env
# Edit DATABASE_URL=sqlite:///./persona.db (default)

# Initialize database
alembic upgrade head

# Start development server
uvicorn api.main:app --reload --port 8000
```

**Visit:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

### Production (PostgreSQL)

```bash
# See SETUP.md and POSTGRES_SETUP.md for full instructions
export DATABASE_URL=postgresql://user:pass@host:5432/persona_hub
export STRIPE_SECRET_KEY=sk_live_...
export RESEND_API_KEY=re_...

alembic upgrade head
docker build -t persona-hub .
docker run -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" persona-hub
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| **[API_DOCS.md](API_DOCS.md)** | Complete API reference (all endpoints, examples, error handling) |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design, deployment architecture, scalability |
| **[SETUP.md](SETUP.md)** | Local development & production deployment guide |
| **[POSTGRES_SETUP.md](POSTGRES_SETUP.md)** | PostgreSQL configuration, backup, replication |
| **[CI_CD_SETUP.md](CI_CD_SETUP.md)** | GitHub Actions workflows, CI/CD automation, Dependabot |
| **[PAYMENT_TESTS.md](PAYMENT_TESTS.md)** | Payment system test documentation |
| **[LOAD_TESTING.md](LOAD_TESTING.md)** | Load testing guide (Locust, K6) |

---

## Core Features

### Authentication & Security

- **Password authentication** — Argon2 hashing, email verification
- **API key management** — SHA-256 hashing with prefix-based lookup
- **Brute force protection** — 5-attempt lockout + 5-minute cooldown
- **Rate limiting** — Per-API-key + per-endpoint throttling
- **Audit logging** — Security events (login, refund, key rotation)
- **CSP nonces** — Per-request script nonce generation
- **CORS** — Restrictive allowlist configuration

### Payment & Billing

- **Stripe integration** — Checkout sessions, subscriptions, invoicing
- **Annual subscriptions** — 20% discount vs. monthly ($99/year basic)
- **Wallet/credits** — User balance tracking, referral rewards
- **Referral program** — $5 credit per successful referral
- **Promo codes** — Discount application and redemption tracking
- **Bundle pricing** — 3 tiers (10/$49, 50/$199, 495/$999)
- **Multi-currency** — 8 currencies with real-time exchange rates
- **Soft delete** — GDPR/KVKK compliance

### API & Integration

- **REST API** — 30+ endpoints (catalog, auth, payments, compile)
- **WebSocket** — Real-time chat with personas
- **Webhook handling** — Stripe idempotency via StripeEvent table
- **Email service** — Resend API integration
- **Voice synthesis** — ElevenLabs text-to-speech
- **Multi-platform** — iOS, Android, Web, Desktop compilation

### DevOps & Reliability

- **Docker** — Multi-stage builds, container deployment
- **Database** — PostgreSQL with streaming replication
- **Backups** — Daily automated S3 backups
- **Health checks** — /health endpoint + post-deploy smoke tests
- **Monitoring** — Request metrics, error rates, latency
- **Auto-scaling** — Horizontal scaling on CPU/memory
- **99.9% SLA** — Multi-AZ deployment, circuit breakers

---

## Technology Stack

```
Frontend:      React / Vue (separate repos)
Backend:       FastAPI (Python 3.11)
Database:      PostgreSQL 13+
Cache:         Redis (optional, for rate limiting)
Payments:      Stripe API
Email:         Resend API
Voice:         ElevenLabs API
Container:     Docker + Docker Compose
CI/CD:         GitHub Actions
Monitoring:    CloudWatch / Datadog / Prometheus
Hosting:       AWS ECS + ALB + RDS
```

---

## Project Structure

```
persona-platform/
├── api/
│   ├── main.py                    # FastAPI app, routes
│   ├── db.py                      # SQLAlchemy models, database helpers
│   ├── auth.py                    # Authentication logic
│   ├── payments.py                # Stripe integration
│   ├── email_service.py           # Resend email integration
│   ├── models.py                  # Pydantic request/response models
│   ├── middleware/
│   │   ├── security_headers.py    # CSP, CORS, HSTS
│   │   ├── rate_limiter.py        # Per-key rate limiting
│   │   ├── audit_logger.py        # Audit trail logging
│   │   └── auth.py                # API key extraction/validation
│   └── routers/
│       ├── catalog.py             # GET /personas
│       ├── compile.py             # POST /v1/compile
│       └── api_keys.py            # API key management
├── tests/
│   ├── test_security_auth.py      # Auth unit tests
│   ├── test_payments_units.py     # Payment logic tests
│   ├── test_payments_integration_simple.py  # E2E tests
│   ├── test_webhooks.py           # Stripe webhook tests
│   ├── load_test_payments.py      # Locust load tests
│   └── load_test_webhooks.js      # K6 webhook tests
├── alembic/
│   ├── versions/
│   │   ├── 001_initial.py
│   │   ├── 002_security_hardening.py
│   │   ├── 003_production_indexes.py
│   │   └── 004_payment_billing.py
│   └── env.py
├── .github/
│   └── workflows/
│       ├── ci-matrix.yml          # Multi-Python testing
│       ├── deploy.yml             # Auto-deploy on main
│       ├── notifications.yml      # Slack/email alerts
│       └── security.yml           # gitleaks, bandit, safety
├── nginx/
│   └── default.conf               # Reverse proxy config
├── Dockerfile                     # Container image
├── docker-compose.yml             # Local dev stack
├── requirements.txt               # Core dependencies
├── requirements-api.txt           # API-specific dependencies
├── API_DOCS.md                    # Complete API reference
├── ARCHITECTURE.md                # System design
├── SETUP.md                       # Development & deployment
├── CI_CD_SETUP.md                 # GitHub Actions guide
└── README.md                      # This file
```

---

## API Endpoints

**Base URL:** `https://api.persona-hub.com` (production) | `http://localhost:8000` (dev)

### System
- `GET /health` — Health check (public)

### Catalog
- `GET /personas` — List all personas (public, paginated)
- `GET /personas/{id}` — Get persona details (public)
- `GET /personas/stats/library` — Library statistics (public)

### Authentication
- `POST /auth/register` — Create account (public)
- `POST /auth/login` — Email + password login (public)
- `POST /auth/request-verification` — Send verification email (public)
- `POST /auth/verify-email` — Verify email with token (public)
- `GET /me` — Get current user profile (authenticated)

### Payments
- `POST /checkout/{persona_id}` — Create checkout session (authenticated)
- `POST /checkout/bundle/{bundle_id}` — Bundle checkout (authenticated)
- `GET /me/wallet` — View credit balance (authenticated)
- `GET /me/invoices` — List invoices (authenticated)
- `POST /me/referral-code` — Generate referral code (authenticated)
- `POST /billing/portal` — Stripe customer portal (authenticated)

### Subscriptions
- `GET /subscription/tiers` — List subscription options (public)
- `POST /subscribe/{tier}` — Create subscription (authenticated)
- `GET /me/subscription` — Get active subscription (authenticated)
- `DELETE /me/subscription` — Cancel subscription (authenticated)

### Compilation
- `POST /v1/compile/{persona_id}` — Compile persona (authenticated)
- `POST /v1/compile/{persona_id}/all-platforms` — All platforms (authenticated)
- `POST /v1/compile/{persona_id}/all-tiers` — All tiers (authenticated)
- `POST /v1/compile/{persona_id}/voice` — Voice synthesis (authenticated)

### WebSocket
- `WebSocket /ws/chat/{persona_id}` — Real-time chat (authenticated)

### Admin
- `POST /admin/refund/{purchase_id}` — Refund purchase (admin only)

**Full API documentation:** See [API_DOCS.md](API_DOCS.md)

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=api --cov-report=html

# Specific test file
pytest tests/test_payments_units.py -v

# Integration tests (requires Stripe test credentials)
pytest tests/test_payments_integration_simple.py -v

# Load testing
python tests/load_test_payments.py --host=localhost:8000

# Security checks
gitleaks detect
bandit -r api/
```

**Test Coverage:** 75%+ (47 tests, 3 skipped for optional dependencies)

---

## Security

### Implemented Features

- ✅ **A1** — Password authentication (Argon2 hashing)
- ✅ **A2** — API key hashing (SHA-256 with prefix)
- ✅ **A3** — Rate limiting (per-key + per-endpoint)
- ✅ **A4** — Email verification (24-hour tokens)
- ✅ **A5** — Brute force protection (5-attempt lockout)
- ✅ **A8** — CSP nonces (per-request generation)
- ✅ **A10** — Key rotation grace period (7 days)
- ✅ **A11** — User enumeration prevention (constant-time comparison)
- ✅ **A12** — CI security scanning (gitleaks, bandit, trivy)
- ✅ **B22** — Audit logging (database + application logs)
- ✅ **G79** — Soft delete (GDPR/KVKK compliance)

### Environment Variables

**Required:**
```bash
DATABASE_URL=postgresql://user:pass@host/db
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Optional:**
```bash
RESEND_API_KEY=re_...                # Email service
REQUIRE_EMAIL_VERIFICATION=true      # Enforce verification
BASE_URL=https://api.persona-hub.com # API URL
CORS_ORIGINS=https://persona-hub.com # CORS allowlist
```

---

## Deployment

### Docker

```bash
# Build
docker build -t persona-hub:latest .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e STRIPE_SECRET_KEY="sk_..." \
  persona-hub:latest
```

### Docker Compose (Development)

```bash
docker-compose up -d
# API: http://localhost:8000
# DB:  postgres://localhost:5432/persona_hub
# Docs: http://localhost:8000/docs
```

### Production Checklist

- [ ] PostgreSQL database provisioned
- [ ] Environment variables configured in secrets manager
- [ ] Stripe API keys (live) configured
- [ ] Resend API key configured
- [ ] TLS certificate installed (nginx)
- [ ] Health check endpoint verified (/health)
- [ ] Backup strategy implemented (daily S3 exports)
- [ ] Monitoring configured (CloudWatch/Datadog)
- [ ] Load balancer health checks enabled
- [ ] CI/CD pipeline green (all tests passing)
- [ ] Post-deploy smoke tests passing
- [ ] Team notified (Slack #deployments)

**See [SETUP.md](SETUP.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for full deployment guide.**

---

## Monitoring & Logs

```bash
# Application logs
docker logs persona-hub

# Database health
psql $DATABASE_URL -c "SELECT version();"

# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# View audit logs
psql $DATABASE_URL -c "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;"

# Stripe webhook health
curl http://localhost:8000/health | jq
```

---

## Performance

| Metric | Target | Actual |
|--------|--------|--------|
| API Response (p95) | <200ms | ~120ms |
| WebSocket Latency | <100ms | ~50ms |
| Database Query | <50ms | ~20ms (with indexes) |
| Compilation | <30s | ~15s (pre-built) |
| Stripe Checkout | <5s | ~3s |

**Optimization strategies:**
- 20+ database indexes (composite keys)
- Connection pooling (20 connections + 10 overflow)
- Response caching (persona catalog: 1 hour)
- Query optimization (explain analyze)
- CDN for static assets (persona images)

---

## Contributing

1. **Branch naming:** `feature/*`, `bugfix/*`, `claude/*`
2. **Commit format:** `type(scope): description` (e.g., `feat(payments): add refund endpoint`)
3. **Code quality:** Run `pre-commit run --all-files` before committing
4. **Tests:** All new features require tests (pytest)
5. **Coverage:** Maintain 75%+ coverage (`pytest --cov=api`)
6. **PR:** Create PR against `develop` branch, not `main`

**See [CI_CD_SETUP.md](CI_CD_SETUP.md) for pre-commit hook setup.**

---

## Roadmap

### H87-H89 ✅ (COMPLETED)
- Multi-Python matrix testing (3.9–3.12)
- GitHub Actions CI/CD automation
- Dependabot dependency updates
- Pre-commit hooks (black, isort, flake8, mypy)
- Slack/email notifications on build status

### H90+ (Planned)
- Canary deployments (10% traffic ramp)
- A/B testing framework
- Automatic rollback detection
- Performance regression alerts
- Advanced observability (tracing, metrics)

### Feature Backlog
- [ ] OAuth login (Google, GitHub)
- [ ] Multi-key API key support
- [ ] Advanced rate limiting (token bucket)
- [ ] GraphQL API
- [ ] WebSocket chat history
- [ ] Mobile app (iOS/Android SDKs)

---

## Support

- **Documentation:** See [API_DOCS.md](API_DOCS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [SETUP.md](SETUP.md)
- **Interactive API Docs:** http://localhost:8000/docs (Swagger UI)
- **GitHub Issues:** https://github.com/mk350174-cmd/persona-platform/issues
- **Email:** support@persona-hub.com

---

## License

Proprietary. © 2024 Persona Platform. All rights reserved.

---

## Changelog

**v1.0.0** — June 2024
- Initial production release
- Complete auth & security implementation
- Payment & billing system
- Compilation pipeline
- CI/CD automation
- 75%+ test coverage
- Multi-Python support (3.9–3.12)
- GDPR/KVKK compliance

**See [CHANGELOG.md](CHANGELOG.md) for detailed history.**
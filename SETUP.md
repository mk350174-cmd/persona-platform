# Development & Deployment Setup

## Local Development

### 1. Clone & Install

```bash
git clone https://github.com/mk350174-cmd/persona-platform.git
cd persona-platform

# Python 3.11+
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r requirements-api.txt  # Optional: API-specific
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env with your values:
```

**Minimal .env (SQLite + no external services):**
```bash
DATABASE_URL=sqlite:///./persona.db
BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Optional: Email verification (requires Resend API key)
# RESEND_API_KEY=re_...

# Optional: Stripe (requires Stripe keys)
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...
```

### 3. Initialize Database

```bash
# Create tables (auto-runs via alembic on startup)
python -c "from api.db import init_db; init_db()"

# Or explicitly run migrations
alembic upgrade head
```

### 4. Start Development Server

```bash
uvicorn api.main:app --reload --port 8000
```

Visit:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Testing

### Unit Tests

```bash
# All tests
pytest tests/

# Security & auth tests
pytest tests/test_security_auth.py -v

# With coverage
pytest tests/ --cov=api --cov-fail-under=80
```

### Manual Testing

**Register:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'
```

**Get Profile (requires API key):**
```bash
curl -H "X-API-Key: prs_..." http://localhost:8000/me
```

---

## Production Deployment

### 1. Database: PostgreSQL

See [POSTGRES_SETUP.md](POSTGRES_SETUP.md) for full setup.

**Quick start:**
```bash
# Create database
createdb persona_hub
createuser persona_app --encrypted --pwprompt

# Set environment
export DATABASE_URL=postgresql://persona_app:password@localhost:5432/persona_hub

# Run migrations
alembic upgrade head
```

### 2. Environment Variables

**Production .env:**
```bash
# Database
DATABASE_URL=postgresql://persona_app:PASSWORD@db.internal:5432/persona_hub

# Security
REQUIRE_EMAIL_VERIFICATION=true
CORS_ORIGINS=https://persona-hub.com,https://www.persona-hub.com

# External APIs
RESEND_API_KEY=re_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
BASE_URL=https://persona-hub.com
```

### 3. Docker Deployment

```dockerfile
# Dockerfile (multi-stage)
FROM python:3.11-slim as base
WORKDIR /app
RUN apt-get update && apt-get install -y gcc postgresql-client

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start server
CMD alembic upgrade head && \
    uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Build & run:**
```bash
docker build -t persona-hub .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e STRIPE_SECRET_KEY="sk_..." \
  persona-hub
```

### 4. Nginx Reverse Proxy

See `nginx/default.conf` (already configured):
- TLS 1.2+, HSTS
- Rate limiting (slowapi backend)
- Gzip compression
- Static file caching

### 5. Health Check & Monitoring

```bash
# Health endpoint (public, no auth)
curl http://localhost:8000/health
# Response: {"status": "ok", "version": "1.0.0", "db": true, "personas": 495}

# Metrics (placeholder for Prometheus)
# curl http://localhost:8000/metrics
```

---

## Security Scanning

### Pre-commit

```bash
# Install pre-commit hook (optional)
pip install pre-commit
pre-commit install

# Or run manually
gitleaks detect --source=github --verbose
bandit -r api/
```

### CI/CD

GitHub Actions automatically runs on PR:
- `gitleaks` — Secret detection
- `bandit` — Python SAST
- `trivy` — Dependency CVE scan

See `.github/workflows/security.yml`

---

## Troubleshooting

### ModuleNotFoundError

```bash
pip install -r requirements.txt
```

### Database Connection Error

```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Port Already in Use

```bash
# Use different port
uvicorn api.main:app --port 8001
```

### Email Verification Not Sending

1. Check RESEND_API_KEY is set
2. Check logs: `tail -f persona_hub.log`
3. Dev mode (RESEND_API_KEY not set): URL printed to stdout

### Rate Limit Issues

- Rate limit state is in-memory; resets on server restart
- For production: configure Redis backend (scale horizontally)
- Check `X-RateLimit-*` headers in response

---

## Key Files

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app, routes, middleware |
| `api/db.py` | SQLAlchemy models, database helpers |
| `api/auth.py` | Authentication (API key, password) |
| `api/models.py` | Pydantic request/response models |
| `api/middleware/` | Security (headers, CSP, rate limiting, audit log) |
| `alembic/` | Database migrations |
| `.github/workflows/` | CI/CD pipelines |
| `tests/` | Unit tests |
| `nginx/` | Reverse proxy config |
| `docker-compose.yml` | Local development stack (optional) |

---

## Documentation

- **Security:** [SECURITY.md](SECURITY.md)
- **Postgres Setup:** [POSTGRES_SETUP.md](POSTGRES_SETUP.md)
- **API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Support

For issues:
1. Check logs: `docker logs persona-hub` or stdout
2. Review [SECURITY.md](SECURITY.md) for security-related questions
3. Check [POSTGRES_SETUP.md](POSTGRES_SETUP.md) for database issues
4. Open a GitHub issue: https://github.com/mk350174-cmd/persona-platform/issues

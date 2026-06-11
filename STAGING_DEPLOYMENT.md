# Staging Environment Deployment Guide

**Platform:** Docker Compose (local or self-hosted)  
**Environment:** Staging  
**Target:** Integration testing, QA, pre-production validation  
**Deployment Time:** 5–10 minutes

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Starting Services](#starting-services)
4. [Health Verification](#health-verification)
5. [Accessing Services](#accessing-services)
6. [Database Management](#database-management)
7. [Data Management](#data-management)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Cleanup & Reset](#cleanup--reset)

---

## Quick Start

### Prerequisites

- Docker (20.10+) and Docker Compose (2.0+)
- Git repository cloned locally
- 4 GB RAM available for all containers
- Ports 80, 443, 3000–3001, 5433, 6380, 8000–8081, 9091 available

### One-Command Deploy

```bash
# Clone and navigate to repo
git clone https://github.com/mk350174-cmd/persona-platform.git
cd persona-platform

# Copy staging environment template
cp .env.staging .env.staging.local

# EDIT .env.staging.local with real API keys:
# - ANTHROPIC_API_KEY
# - ELEVENLABS_API_KEY
# - STRIPE_SECRET_KEY (use TEST keys)
# - RESEND_API_KEY
nano .env.staging.local

# Run automated setup
bash scripts/staging-setup.sh

# Verify all services are running
docker-compose -f docker-compose.staging.yml ps
```

### Expected Output

```
NAME                              STATUS
persona-api-staging               Up (healthy)
persona-postgres-staging          Up (healthy)
persona-redis-staging             Up (healthy)
persona-nginx-staging             Up (healthy)
persona-backup-staging            Up
persona-adminer-staging           Up (healthy)
persona-prometheus-staging        Up
persona-grafana-staging           Up (healthy)
```

---

## Environment Setup

### 1. Configure Staging Variables

Copy the template environment file:

```bash
cp .env.staging .env.staging.local
```

Edit `.env.staging.local` with real values for your staging deployment:

```bash
nano .env.staging.local
```

**Required changes:**

```bash
# 1. API Keys (get from service dashboards)
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
ELEVENLABS_API_KEY=el_YOUR-KEY-HERE
STRIPE_SECRET_KEY=sk_test_YOUR-TEST-KEY  # Must be TEST key
RESEND_API_KEY=re_YOUR-KEY-HERE

# 2. Security
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. Email (where to send staging notifications)
FROM_EMAIL=noreply-staging@yourdomain.com
TEST_EMAIL_RECIPIENT=your-email@example.com

# 4. Database credentials (optional: change if sharing staging)
POSTGRES_USER=staging_user
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# 5. Grafana admin password
GRAFANA_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
```

### 2. Verify Docker Daemon Running

```bash
docker ps
# Should list containers without error
```

### 3. Validate Ports Available

```bash
# Check if required ports are free
lsof -i :80 || echo "✓ Port 80 available"
lsof -i :443 || echo "✓ Port 443 available"
lsof -i :8000 || echo "✓ Port 8000 available"
lsof -i :5433 || echo "✓ Port 5433 available"
lsof -i :6380 || echo "✓ Port 6380 available"
```

---

## Starting Services

### Full Automated Setup

```bash
bash scripts/staging-setup.sh
```

This script:
- ✓ Validates Docker and ports
- ✓ Loads environment variables
- ✓ Builds Docker images if needed
- ✓ Creates staging network
- ✓ Starts all containers
- ✓ Waits for health checks
- ✓ Displays access URLs

### Manual Startup

If you prefer step-by-step control:

```bash
# 1. Build images (if not cached)
docker-compose -f docker-compose.staging.yml build

# 2. Start services in background
docker-compose -f docker-compose.staging.yml up -d

# 3. View startup logs (press Ctrl+C to exit)
docker-compose -f docker-compose.staging.yml logs -f

# 4. Wait for health checks to pass (1-2 minutes)
sleep 30 && docker-compose -f docker-compose.staging.yml ps
```

### Expected Timeline

| Service | Start Time | Ready for Testing |
|---------|-----------|-------------------|
| PostgreSQL | 5 sec | After health check (15 sec) |
| Redis | 3 sec | After health check (5 sec) |
| Nginx | 5 sec | After health check (10 sec) |
| API | 10-15 sec | After migrations + health check (30 sec) |
| Backup | 5 sec | Immediately (background cron) |
| Adminer | 8 sec | After startup (10 sec) |
| Prometheus | 5 sec | Immediately |
| Grafana | 10 sec | After startup (10–15 sec) |

**Total Ready Time:** 1–2 minutes

---

## Health Verification

### Automated Health Check Script

```bash
bash scripts/staging-health-check.sh
```

This verifies:
- ✓ All containers running
- ✓ API responds to health check
- ✓ PostgreSQL database accessible
- ✓ Redis cache responding
- ✓ Nginx reverse proxy healthy

### Manual Health Verification

#### 1. Check Container Status

```bash
docker-compose -f docker-compose.staging.yml ps

# All should show "Up" status
# Healthy containers show "(healthy)"
```

#### 2. Test API Health Endpoint

```bash
curl -s http://localhost:8000/health | jq .

# Expected response:
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "db": true,
#   "personas": 495,
#   "timestamp": "2024-06-11T10:30:45Z"
# }
```

#### 3. Test Database Connection

```bash
docker-compose -f docker-compose.staging.yml exec postgres \
  psql -U staging_user -d persona_hub_staging -c "SELECT version();"

# Expected: PostgreSQL version output
```

#### 4. Test Redis Connection

```bash
docker-compose -f docker-compose.staging.yml exec redis \
  redis-cli ping

# Expected: PONG
```

#### 5. Test API Endpoints

```bash
# List all personas (public endpoint, no auth required)
curl -s http://localhost:8000/personas?limit=5 | jq '.data | length'
# Expected: 5

# Register test user
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@staging.com","password":"Test1234!"}' | jq '.user.email'
# Expected: test@staging.com

# Get user account
curl -s http://localhost:8000/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" | jq '.email'
```

---

## Accessing Services

### API & Web

| Service | URL | Notes |
|---------|-----|-------|
| **API** | http://localhost:8000 | Main FastAPI application |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **API Redoc** | http://localhost:8000/redoc | ReDoc documentation |
| **Health Check** | http://localhost:8000/health | System status |

### Database Administration

| Service | URL | Credentials |
|---------|-----|-------------|
| **Adminer** | http://localhost:8081 | User: `staging_user` / Password: from `.env.staging.local` |
| **psql CLI** | localhost:5433 | `psql postgresql://staging_user:PASSWORD@localhost:5433/persona_hub_staging` |

### Monitoring & Dashboards

| Service | URL | Login |
|---------|-----|-------|
| **Prometheus** | http://localhost:9091 | No auth required |
| **Grafana** | http://localhost:3001 | admin / (password from `.env.staging.local`) |

### Quick Access Commands

```bash
# Connect to API container shell
docker-compose -f docker-compose.staging.yml exec api sh

# Connect to PostgreSQL directly
docker-compose -f docker-compose.staging.yml exec postgres \
  psql -U staging_user -d persona_hub_staging

# Connect to Redis CLI
docker-compose -f docker-compose.staging.yml exec redis redis-cli

# View Adminer in browser
open http://localhost:8081

# View Grafana dashboards
open http://localhost:3001
```

---

## Database Management

### View Database Schema

```bash
docker-compose -f docker-compose.staging.yml exec postgres \
  psql -U staging_user -d persona_hub_staging -c "\dt"

# List all tables
```

### Run Database Migrations

Migrations run automatically on API startup. To manually run:

```bash
# Connect to API container and run Alembic
docker-compose -f docker-compose.staging.yml exec api \
  alembic upgrade head

# Check current migration status
docker-compose -f docker-compose.staging.yml exec api \
  alembic current
```

### Create Database Backup

```bash
# Backup filename with timestamp
BACKUP_FILE="persona_staging_$(date +%Y%m%d_%H%M%S).sql"

# Create backup
docker-compose -f docker-compose.staging.yml exec postgres \
  pg_dump -U staging_user persona_hub_staging > "/tmp/$BACKUP_FILE"

echo "Backup created: /tmp/$BACKUP_FILE"

# List backups
ls -lh /tmp/persona_staging_*.sql
```

### Restore Database from Backup

```bash
BACKUP_FILE="/path/to/persona_staging_20240611_103045.sql"

# Restore backup
docker-compose -f docker-compose.staging.yml exec -T postgres \
  psql -U staging_user persona_hub_staging < "$BACKUP_FILE"

echo "Database restored from: $BACKUP_FILE"
```

### Reset Database to Fresh State

```bash
# WARNING: This deletes all data in staging database

# Stop services
docker-compose -f docker-compose.staging.yml down

# Remove database volume (DESTRUCTIVE)
docker volume rm persona-platform_staging_postgres_data

# Restart services (recreates database)
docker-compose -f docker-compose.staging.yml up -d

# Wait for health checks
sleep 30

# Verify fresh database
curl -s http://localhost:8000/health | jq .
```

---

## Data Management

### Seed Test Data

If a seed script exists (`scripts/staging/seed-data.sql`), it runs automatically on database creation.

To manually seed:

```bash
docker-compose -f docker-compose.staging.yml exec postgres \
  psql -U staging_user persona_hub_staging < scripts/staging/seed-data.sql
```

### Generate Test Users

```bash
# Create 5 test users for QA
for i in {1..5}; do
  curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"test$i@staging.com\",
      \"password\": \"TestPassword$i!\"
    }"
  echo "Created test$i@staging.com"
done
```

### Clear Cache (Redis)

```bash
docker-compose -f docker-compose.staging.yml exec redis \
  redis-cli FLUSHALL

echo "✓ All Redis keys cleared"
```

### Export Data for Testing

```bash
# Export personas as JSON
curl -s "http://localhost:8000/personas?limit=495" | jq > personas_export.json

# Export users (requires auth token)
curl -s "http://localhost:8000/admin/users" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" | jq > users_export.json
```

---

## Monitoring & Logs

### View Service Logs

```bash
# All services
docker-compose -f docker-compose.staging.yml logs -f

# Specific service (tail last 100 lines, follow new)
docker-compose -f docker-compose.staging.yml logs -f --tail=100 api
docker-compose -f docker-compose.staging.yml logs -f --tail=100 postgres
docker-compose -f docker-compose.staging.yml logs -f --tail=100 nginx

# Get logs for specific time range
docker-compose -f docker-compose.staging.yml logs --since 10m --until 2m api
```

### Check Resource Usage

```bash
# Monitor container resource usage in real-time
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Example output:
# CONTAINER                   CPU %               MEM USAGE / LIMIT
# persona-api-staging         0.05%               245.2MiB / 512MiB
# persona-postgres-staging    0.02%               156.8MiB / 384MiB
# persona-redis-staging       0.01%               8.4MiB / 256MiB
```

### View Prometheus Metrics

```bash
# Access Prometheus UI
open http://localhost:9091

# Query examples in Prometheus:
# - rate(http_requests_total[5m])  # Request rate per 5 min
# - histogram_quantile(0.95, http_request_duration_seconds)  # 95th percentile latency
# - container_memory_usage_bytes  # Memory per container
```

### View Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3001

# Login: admin / (password from .env.staging.local)
# Navigate to: Home > Dashboards > Browse
```

### API Request Logging

API logs are written to the `staging_api_logs` volume:

```bash
# View API logs
docker-compose -f docker-compose.staging.yml exec api \
  tail -f /app/logs/app.log

# Search for errors
docker-compose -f docker-compose.staging.yml exec api \
  grep ERROR /app/logs/app.log | tail -20
```

---

## Troubleshooting

### Container Won't Start

**Symptom:** Container exits immediately or shows "Exited (1)"

```bash
# Check container logs for errors
docker-compose -f docker-compose.staging.yml logs api

# Example error: "Address already in use"
# Solution: Check port availability
lsof -i :8000
# Kill conflicting process or free the port
```

### Slow Response Times

**Symptom:** API requests take >1s to respond

```bash
# 1. Check container resource usage
docker stats persona-api-staging

# 2. Check API logs for slow queries
docker-compose -f docker-compose.staging.yml logs api | grep "slow"

# 3. Check database connections
docker-compose -f docker-compose.staging.yml exec postgres \
  psql -U staging_user -d persona_hub_staging -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Restart API to clear connection pool
docker-compose -f docker-compose.staging.yml restart api
```

### Database Connection Error

**Symptom:** API logs show "could not connect to server"

```bash
# 1. Verify PostgreSQL is healthy
docker-compose -f docker-compose.staging.yml ps postgres
# Should show "(healthy)"

# 2. Test PostgreSQL directly
docker-compose -f docker-compose.staging.yml exec postgres pg_isready -U staging_user

# 3. Check DATABASE_URL in .env.staging.local
cat .env.staging.local | grep DATABASE_URL

# 4. Restart PostgreSQL
docker-compose -f docker-compose.staging.yml restart postgres
```

### Redis Connection Error

**Symptom:** Cache operations fail in logs

```bash
# 1. Verify Redis is running
docker-compose -f docker-compose.staging.yml exec redis redis-cli ping
# Should output: PONG

# 2. Check REDIS_URL in .env.staging.local
cat .env.staging.local | grep REDIS_URL

# 3. Monitor Redis memory
docker-compose -f docker-compose.staging.yml exec redis \
  redis-cli INFO memory

# 4. Restart Redis
docker-compose -f docker-compose.staging.yml restart redis
```

### Nginx Not Routing to API

**Symptom:** Port 80/443 show "502 Bad Gateway"

```bash
# 1. Check Nginx configuration
docker-compose -f docker-compose.staging.yml exec nginx \
  nginx -t

# 2. Check if API is healthy
curl -s http://localhost:8000/health

# 3. Check Nginx logs
docker-compose -f docker-compose.staging.yml logs nginx | grep -i error

# 4. Restart Nginx
docker-compose -f docker-compose.staging.yml restart nginx
```

### Migrations Failed

**Symptom:** API logs show "Alembic migration error"

```bash
# 1. Check current migration status
docker-compose -f docker-compose.staging.yml exec api \
  alembic current

# 2. Check migration history
docker-compose -f docker-compose.staging.yml exec api \
  alembic history

# 3. Manually downgrade and upgrade
docker-compose -f docker-compose.staging.yml exec api \
  alembic downgrade -1

docker-compose -f docker-compose.staging.yml exec api \
  alembic upgrade head

# 4. If stuck, reset database
docker-compose -f docker-compose.staging.yml down -v
docker-compose -f docker-compose.staging.yml up -d
```

### Out of Memory

**Symptom:** Container killed with "OOMKilled" or "Cannot allocate memory"

```bash
# 1. Check current resource usage
docker stats

# 2. Find memory hogs
docker stats --format "table {{.Container}}\t{{.MemUsage}}" | sort -k2 -h

# 3. Increase memory limits in docker-compose.staging.yml
# Edit: deploy.resources.limits.memory

# 4. Restart containers
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d
```

### DNS/Network Issues

**Symptom:** Containers can't reach each other (e.g., "postgres: Name or service not known")

```bash
# 1. Check staging network exists
docker network ls | grep staging

# 2. Inspect network
docker network inspect persona-platform_staging

# 3. Verify containers on network
docker network inspect persona-platform_staging | jq '.Containers'

# 4. Recreate network (DESTRUCTIVE)
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d
```

---

## Cleanup & Reset

### Stop All Services

```bash
docker-compose -f docker-compose.staging.yml down

# Output should show:
# Stopping persona-api-staging ... done
# Stopping persona-postgres-staging ... done
# [etc...]
```

### Stop & Keep Data

```bash
# Stop containers but keep volumes (data persists)
docker-compose -f docker-compose.staging.yml stop

# Resume later with:
docker-compose -f docker-compose.staging.yml start
```

### Full Cleanup (Removes All Data)

```bash
# WARNING: This deletes all staging data permanently

docker-compose -f docker-compose.staging.yml down -v

# Verify volumes removed
docker volume ls | grep staging
# Should show no results
```

### Remove Unused Docker Resources

```bash
# Clean up dangling images and networks
docker system prune -a --volumes

# This removes:
# - Unused containers
# - Unused images
# - Unused networks
# - Unused volumes (unless they have names)
```

---

## Appendix: Common Commands

```bash
# Start staging
docker-compose -f docker-compose.staging.yml up -d

# View status
docker-compose -f docker-compose.staging.yml ps

# Follow logs
docker-compose -f docker-compose.staging.yml logs -f

# Restart service
docker-compose -f docker-compose.staging.yml restart api

# View environment
docker-compose -f docker-compose.staging.yml config | grep -A 20 "environment:"

# Execute command in container
docker-compose -f docker-compose.staging.yml exec api python -c "..."

# View one-time output (no tail)
docker-compose -f docker-compose.staging.yml logs --tail=50

# Down and remove volumes
docker-compose -f docker-compose.staging.yml down -v

# Export compose config with environment substituted
docker-compose -f docker-compose.staging.yml config > /tmp/staging-resolved.yml
```

---

## Getting Help

For issues or questions:

1. **Check logs first:** `docker-compose -f docker-compose.staging.yml logs -f`
2. **Run health check:** `bash scripts/staging-health-check.sh`
3. **Review this guide:** Search for your symptom in Troubleshooting section
4. **Open an issue:** https://github.com/mk350174-cmd/persona-platform/issues

---

**Last Updated:** June 2024  
**Maintained by:** Persona Platform Team  
**License:** See LICENSE file in repository root

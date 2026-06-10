# PostgreSQL Production Setup

## Local Development (SQLite)

```bash
export DATABASE_URL="sqlite:///./persona.db"
python -m uvicorn api.main:app --reload
```

## Production (PostgreSQL)

### 1. Create Database

```bash
# As postgres superuser
createdb persona_hub
createuser persona_app --encrypted --pwprompt
psql -d persona_hub -c "GRANT CONNECT ON DATABASE persona_hub TO persona_app;"
psql -d persona_hub -c "GRANT USAGE ON SCHEMA public TO persona_app;"
psql -d persona_hub -c "GRANT CREATE ON SCHEMA public TO persona_app;"
```

### 2. Configure Environment

```bash
# .env or env vars
DATABASE_URL=postgresql://persona_app:${PASSWORD}@localhost:5432/persona_hub
```

### 3. Apply Migrations

```bash
alembic upgrade head
```

This will:
- Create all tables (users, purchases, subscriptions, api_key_rotation, audit_log, etc.)
- Create initial schema (migration 98e96cff2d3b)
- Add security fields: api_key_hash, password_hash, deleted_at, email_verified, etc. (migration a1b2c3d4e5f6)
- Add production indexes for common queries (migration b2c3d4e5f6a7)

### 4. Connection Pooling

For production, configure connection pooling in `api/db.py`:

```python
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,           # Default: 5
        max_overflow=10,        # Allow 10 extra connections
        pool_pre_ping=True,     # Verify connections before use
        pool_recycle=3600,      # Recycle connections after 1 hour
    )
```

### 5. Backup Strategy

```bash
# Daily backup
pg_dump persona_hub | gzip > /backups/persona_hub_$(date +%Y%m%d).sql.gz

# Restore
gunzip < /backups/persona_hub_20260610.sql.gz | psql persona_hub
```

### 6. Monitoring

```bash
# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check index bloat
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE schemaname = 'public' 
ORDER BY idx_scan DESC;
```

### 7. Performance Tuning

**postgresql.conf settings for small-to-medium deployments:**

```ini
# Memory
shared_buffers = 256MB              # ~25% of system RAM
effective_cache_size = 1GB          # ~50-75% of system RAM
work_mem = 16MB

# WAL (Write-Ahead Log)
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB

# Query optimization
random_page_cost = 1.1              # For SSD
effective_io_concurrency = 200

# Logging
log_min_duration_statement = 1000   # Log slow queries (>1s)
log_connections = on
log_disconnections = on
```

### 8. Scaling to Replication

Once beyond single-node:

```bash
# On primary (master)
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET wal_keep_size = 2GB;
SELECT pg_reload_conf();

# On replica (standby)
basebackup -D /var/lib/postgresql/16/main --progress
# standby.signal to mark as standby
```

## Key Differences: SQLite → PostgreSQL

| Feature | SQLite | PostgreSQL |
|---------|--------|-----------|
| Concurrent writes | Limited (file lock) | Full MVCC |
| Connection pooling | Not needed | Required (pool_size=20) |
| Indexes | Single file | Separate tablespace |
| Transactions | Exclusive lock | Row-level locks |
| Backup | File copy | pg_dump + WAL |
| Replication | None | Streaming replication |

## Alembic Migrations

```bash
# Generate new migration (auto-detect schema changes)
alembic revision --autogenerate -m "Add user roles"

# List applied migrations
alembic history

# Downgrade to previous (DANGEROUS in production)
alembic downgrade -1  # NOT recommended for live data
```

## Index Maintenance

```bash
# Reindex (if bloat accumulates)
REINDEX TABLE users;

# ANALYZE to update statistics
ANALYZE;

# VACUUM to reclaim space (run weekly or with autovacuum)
VACUUM ANALYZE;
```

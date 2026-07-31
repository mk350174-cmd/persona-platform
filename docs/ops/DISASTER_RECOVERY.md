# Disaster Recovery Plan — persona-platform API

**Status: draft plan, not yet exercised against production infrastructure.**
There is no live deployment yet (no staging/production account exists —
T2-044/T2-048/T2-049 are blocked on the user setting one up). This
document describes the intended procedure and the tooling that backs it;
it is not a record of drills that have actually happened. Once a real
environment exists, the first real dry-run should update this file with
the actual date, duration, and any gaps found — do not backfill a false
history here.

## Scope

Covers the FastAPI backend (`api/`) and its database. Does not cover a
frontend deployment (T2-032..042 deferred — see `GELISTIRME_GOREV_TAKIP.md`),
since none is deployed by this repo.

## Backup

- `scripts/db_backup.sh` — dumps the database to `$BACKUP_DIR` (default
  `./backups`). Works against both supported `DATABASE_URL` forms:
  SQLite (dev) via Python's `sqlite3.backup()`, PostgreSQL (prod, ADR 0001)
  via `pg_dump`.
- **Verified in this repo's sandbox** (2026-07-31): backup → deliberately
  corrupt the live SQLite file → restore → confirmed the recovered database
  reads back correctly (`scripts/db_restore.sh`). The PostgreSQL path uses
  standard `pg_dump`/`psql` and has not been exercised against a real
  Postgres instance yet — no such instance exists in this environment.
- **Not yet decided:** backup schedule/retention (needs a real deployment
  target — cron on what host, retained for how long, where stored). A
  reasonable starting point once infrastructure exists: nightly dump,
  7 daily + 4 weekly retained, shipped to object storage (S3/R2/etc. —
  T2-049, blocked-business).

## Restore

`CONFIRM=yes scripts/db_restore.sh <backup-file>` — refuses to run without
the explicit `CONFIRM=yes` guard, since it overwrites the current database.

## Failure scenarios and response

| Scenario | Response |
|---|---|
| API process crash/OOM | Process manager (systemd/container orchestrator) restarts it. `/health` endpoint exists for a liveness probe. No orchestration config is committed yet — depends on the actual deploy target. |
| Database corruption | Stop the API, run `scripts/db_restore.sh` against the most recent good backup, restart. Data since that backup is lost — this is why backup frequency matters once real traffic exists. |
| Bad deploy (new code breaks the API) | See `docs/ops/ROLLBACK.md` — revert to the last known-good image/commit. |
| Stripe webhook secret compromised | Rotate `STRIPE_WEBHOOK_SECRET` and `STRIPE_SECRET_KEY` in the secrets manager, redeploy. Old webhook signatures stop verifying immediately (by design). |
| JWT secret compromised | Rotate `JWT_SECRET_KEY`. All existing tokens become invalid immediately — every logged-in user is signed out. No token-revocation-list exists for partial invalidation; this is an accepted gap for the current scale. |

## Open gaps (honest, not resolved yet)

- No real staging/production environment to test any of this against.
- No monitoring/alerting wired up yet (T2-028/029/030 — blocked on real
  Sentry/PostHog/Prometheus accounts).
- No automated backup schedule — the script exists and works, nothing
  invokes it on a timer yet.
- PostgreSQL backup/restore path is implemented but untested against a
  real Postgres instance.

#!/usr/bin/env python3
"""
Persona Platform — Database Health Check Script

Checks the health of the application database and reports one of three states:
    healthy   — all checks pass
    degraded  — connection OK but some non-critical checks failed
    down      — cannot reach the database

Checks performed:
    1. Connection test (can we open a session?)
    2. Row counts in key tables (users, purchases, subscriptions)
    3. Alembic schema version
    4. PostgreSQL-only: replication lag (if pg_stat_replication is available)
    5. Response time (query latency)

Exit codes:
    0  — healthy
    1  — degraded
    2  — down
    3  — unexpected script error

Usage:
    python scripts/healthcheck.py
    python scripts/healthcheck.py --db-url postgresql://user:pass@host/db
    python scripts/healthcheck.py --db-url $DATABASE_URL --json
    python scripts/healthcheck.py --warn-rows 0 --warn-latency-ms 500
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("persona.healthcheck")

# ---------------------------------------------------------------------------
# Result constants
# ---------------------------------------------------------------------------

STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"

EXIT_HEALTHY = 0
EXIT_DEGRADED = 1
EXIT_DOWN = 2
EXIT_ERROR = 3

# Key tables to check — add any new tables here
KEY_TABLES = [
    "users",
    "purchases",
    "subscriptions",
]

# Tables that are allowed to be empty in a fresh deployment
ALLOW_EMPTY_TABLES = {
    "purchases",
    "subscriptions",
}

# ---------------------------------------------------------------------------
# Individual health checks
# ---------------------------------------------------------------------------

def check_connection(engine) -> dict:
    """
    Verify the database engine can open a connection and execute a trivial
    query.

    Returns a result dict:
        ok (bool), latency_ms (float), error (str|None)
    """
    start = time.monotonic()
    try:
        with engine.connect() as conn:
            conn.execute(_select_one(engine))
        latency_ms = (time.monotonic() - start) * 1000
        return {"ok": True, "latency_ms": round(latency_ms, 2), "error": None}
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {"ok": False, "latency_ms": round(latency_ms, 2), "error": str(exc)}


def _select_one(engine):
    """Return a dialect-appropriate trivial SELECT expression."""
    from sqlalchemy import text
    if engine.dialect.name == "sqlite":
        return text("SELECT 1")
    return text("SELECT 1")


def check_table_counts(engine, tables: list[str]) -> dict:
    """
    COUNT(*) each table in *tables* and return a result dict:
        ok (bool), counts (dict[table->int]), errors (list[str])
    """
    from sqlalchemy import text

    counts: dict[str, int] = {}
    errors: list[str] = []

    with engine.connect() as conn:
        for table in tables:
            try:
                row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                counts[table] = row[0] if row else 0
            except Exception as exc:
                errors.append(f"{table}: {exc}")
                counts[table] = -1

    ok = len(errors) == 0
    return {"ok": ok, "counts": counts, "errors": errors}


def check_schema_version(engine) -> dict:
    """
    Read the current Alembic migration head from the ``alembic_version`` table.

    Returns:
        ok (bool), version (str|None), error (str|None)
    """
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).fetchone()
            version = row[0] if row else None
        return {"ok": version is not None, "version": version, "error": None}
    except Exception as exc:
        return {"ok": False, "version": None, "error": str(exc)}


def check_replication_lag(engine) -> Optional[dict]:
    """
    Query ``pg_stat_replication`` for replication lag (Postgres only).
    Returns None for non-Postgres engines.

    Returns dict with:
        ok (bool), replicas (int), max_lag_bytes (int|None), error (str|None)
    """
    if engine.dialect.name != "postgresql":
        return None

    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT
                        client_addr,
                        state,
                        sent_lsn - replay_lsn AS lag_bytes
                    FROM pg_stat_replication
                    """
                )
            ).fetchall()

        if not rows:
            # No streaming replicas — acceptable for single-node deployments
            return {
                "ok": True,
                "replicas": 0,
                "max_lag_bytes": None,
                "error": None,
                "note": "No streaming replicas found (single-node deployment).",
            }

        lag_values = [r[2] for r in rows if r[2] is not None]
        max_lag = max(lag_values) if lag_values else 0
        # Warn if lag > 100 MB
        ok = max_lag < 100 * 1024 * 1024

        return {
            "ok": ok,
            "replicas": len(rows),
            "max_lag_bytes": max_lag,
            "error": None,
        }
    except Exception as exc:
        return {"ok": False, "replicas": 0, "max_lag_bytes": None, "error": str(exc)}


def check_write_roundtrip(engine) -> dict:
    """
    Verify the database accepts writes by inserting and immediately deleting
    a sentinel row in a temporary table (or using a simple transaction rollback).

    Returns:
        ok (bool), latency_ms (float), error (str|None)
    """
    from sqlalchemy import text

    start = time.monotonic()
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                # SQLite: use a SAVEPOINT-based rollback
                conn.execute(text("CREATE TABLE IF NOT EXISTS _hc_sentinel (id INTEGER PRIMARY KEY)"))
                conn.execute(text("INSERT INTO _hc_sentinel VALUES (999999999)"))
                conn.execute(text("DELETE FROM _hc_sentinel WHERE id = 999999999"))
            else:
                # Postgres: begin, insert to pg_temp, rollback
                conn.execute(text("CREATE TEMP TABLE IF NOT EXISTS _hc_sentinel (id BIGINT) ON COMMIT DROP"))
                conn.execute(text("INSERT INTO _hc_sentinel VALUES (999999999)"))
                conn.execute(text("DELETE FROM _hc_sentinel WHERE id = 999999999"))

        latency_ms = (time.monotonic() - start) * 1000
        return {"ok": True, "latency_ms": round(latency_ms, 2), "error": None}
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {"ok": False, "latency_ms": round(latency_ms, 2), "error": str(exc)}


# ---------------------------------------------------------------------------
# Aggregate health check
# ---------------------------------------------------------------------------

def run_healthcheck(
    db_url: str,
    *,
    warn_rows: int = 0,
    warn_latency_ms: float = 1000.0,
    tables: Optional[list[str]] = None,
) -> dict:
    """
    Execute all health checks and return an aggregate report dict.

    Report keys:
        status         — "healthy" | "degraded" | "down"
        timestamp      — ISO-8601 UTC
        database_url   — sanitised (password redacted)
        checks         — dict of individual check results
        summary        — human-readable summary string
    """
    from sqlalchemy import create_engine as _create_engine

    if tables is None:
        tables = KEY_TABLES

    report: dict[str, Any] = {
        "status": STATUS_HEALTHY,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "database_url": _sanitise_url(db_url),
        "checks": {},
        "summary": "",
    }

    issues: list[str] = []
    warnings: list[str] = []

    # ── 1. Connection ──────────────────────────────────────────────────────
    try:
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        engine = _create_engine(db_url, connect_args=connect_args)
    except Exception as exc:
        report["status"] = STATUS_DOWN
        report["checks"]["connection"] = {"ok": False, "error": str(exc)}
        report["summary"] = f"DOWN: Cannot create engine — {exc}"
        return report

    conn_result = check_connection(engine)
    report["checks"]["connection"] = conn_result

    if not conn_result["ok"]:
        report["status"] = STATUS_DOWN
        report["summary"] = f"DOWN: Cannot connect — {conn_result['error']}"
        # No point running further checks if we can't connect
        return report

    if conn_result["latency_ms"] > warn_latency_ms:
        warnings.append(
            f"Connection latency {conn_result['latency_ms']:.0f} ms exceeds "
            f"threshold {warn_latency_ms:.0f} ms"
        )

    # ── 2. Table counts ────────────────────────────────────────────────────
    count_result = check_table_counts(engine, tables)
    report["checks"]["table_counts"] = count_result

    if not count_result["ok"]:
        issues.extend(count_result["errors"])

    for table, count in count_result["counts"].items():
        if count == 0 and table not in ALLOW_EMPTY_TABLES and warn_rows == 0:
            warnings.append(f"Table '{table}' has 0 rows (may indicate a fresh or empty DB)")
        elif count < warn_rows:
            warnings.append(f"Table '{table}' has {count} rows (below threshold {warn_rows})")

    # ── 3. Schema version ─────────────────────────────────────────────────
    schema_result = check_schema_version(engine)
    report["checks"]["schema_version"] = schema_result

    if not schema_result["ok"]:
        warnings.append(
            "Alembic version unavailable — "
            f"{schema_result.get('error', 'unknown error')}"
        )

    # ── 4. Replication lag (Postgres only) ─────────────────────────────────
    repl_result = check_replication_lag(engine)
    if repl_result is not None:
        report["checks"]["replication"] = repl_result
        if not repl_result["ok"]:
            warnings.append(
                f"Replication lag high: {repl_result.get('max_lag_bytes', '?')} bytes "
                f"on {repl_result.get('replicas', '?')} replica(s)"
            )

    # ── 5. Write round-trip ────────────────────────────────────────────────
    write_result = check_write_roundtrip(engine)
    report["checks"]["write_roundtrip"] = write_result

    if not write_result["ok"]:
        issues.append(f"Write round-trip failed: {write_result['error']}")

    # ── Aggregate status ───────────────────────────────────────────────────
    if issues:
        report["status"] = STATUS_DEGRADED
        report["summary"] = "DEGRADED: " + "; ".join(issues)
    elif warnings:
        report["status"] = STATUS_DEGRADED
        report["summary"] = "DEGRADED: " + "; ".join(warnings)
    else:
        table_info = ", ".join(
            f"{t}={count_result['counts'].get(t, '?')}"
            for t in tables
        )
        latency = conn_result["latency_ms"]
        version = schema_result.get("version") or "unknown"
        report["summary"] = (
            f"HEALTHY: latency={latency:.0f}ms, "
            f"schema={version}, rows=[{table_info}]"
        )

    if warnings:
        report["warnings"] = warnings
    if issues:
        report["issues"] = issues

    return report


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sanitise_url(url: str) -> str:
    """Return the database URL with password replaced by '***'."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
            sanitised = parsed._replace(netloc=netloc)
            return urlunparse(sanitised)
    except Exception:
        pass
    return url


def _status_to_exit(status: str) -> int:
    return {
        STATUS_HEALTHY: EXIT_HEALTHY,
        STATUS_DEGRADED: EXIT_DEGRADED,
        STATUS_DOWN: EXIT_DOWN,
    }.get(status, EXIT_ERROR)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persona Platform database health check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./persona_store.db"),
        dest="db_url",
        help="SQLAlchemy database URL (default: $DATABASE_URL or SQLite dev path)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=KEY_TABLES,
        help=f"Tables to count (default: {' '.join(KEY_TABLES)})",
    )
    parser.add_argument(
        "--warn-rows",
        type=int,
        default=0,
        dest="warn_rows",
        help="Warn if any key table has fewer than N rows (default: 0 = disabled)",
    )
    parser.add_argument(
        "--warn-latency-ms",
        type=float,
        default=1000.0,
        dest="warn_latency_ms",
        help="Warn if connection latency exceeds N ms (default: 1000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output full report as JSON",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only print the status line (suppress check details)",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        report = run_healthcheck(
            db_url=args.db_url,
            warn_rows=args.warn_rows,
            warn_latency_ms=args.warn_latency_ms,
            tables=args.tables,
        )
    except Exception as exc:
        log.error("Health check script error: %s", exc, exc_info=args.verbose)
        return EXIT_ERROR

    if args.output_json:
        print(json.dumps(report, indent=2))
    elif args.quiet:
        print(report["summary"])
    else:
        status = report["status"]
        print(f"\nDatabase Health Report — {report['timestamp']}")
        print(f"URL     : {report['database_url']}")
        print(f"Status  : {status.upper()}")
        print(f"Summary : {report['summary']}")
        print()

        checks = report.get("checks", {})

        # Connection
        conn = checks.get("connection", {})
        print(
            f"  [{'OK' if conn.get('ok') else 'FAIL'}] Connection — "
            f"latency {conn.get('latency_ms', '?')} ms"
        )

        # Table counts
        tc = checks.get("table_counts", {})
        for table, count in tc.get("counts", {}).items():
            indicator = "OK" if count >= 0 else "FAIL"
            print(f"  [{indicator}] {table:<35} {count:>10} rows")

        # Schema version
        sv = checks.get("schema_version", {})
        if sv:
            indicator = "OK" if sv.get("ok") else "WARN"
            ver = sv.get("version") or sv.get("error") or "unknown"
            print(f"  [{indicator}] Schema version — {ver}")

        # Replication
        repl = checks.get("replication")
        if repl:
            indicator = "OK" if repl.get("ok") else "WARN"
            lag = repl.get("max_lag_bytes")
            replicas = repl.get("replicas", 0)
            lag_str = f"{lag / 1024:.1f} KB lag" if lag else "no lag data"
            print(f"  [{indicator}] Replication — {replicas} replica(s), {lag_str}")

        # Write round-trip
        wr = checks.get("write_roundtrip", {})
        if wr:
            indicator = "OK" if wr.get("ok") else "FAIL"
            print(
                f"  [{indicator}] Write round-trip — "
                f"latency {wr.get('latency_ms', '?')} ms"
            )

        # Warnings / issues
        for w in report.get("warnings", []):
            print(f"\n  WARN: {w}")
        for i in report.get("issues", []):
            print(f"\n  ISSUE: {i}")

        print()

    return _status_to_exit(report["status"])


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Persona Platform — Database Restore Script

Restores SQLite or PostgreSQL databases from gzip-compressed backup files
produced by scripts/backup.py.  Optionally downloads the backup from S3
before restoring.

Usage:
    # Restore SQLite
    python scripts/restore.py \\
        --backup /tmp/backups/persona_store_backup_20240101T020000Z.db.gz \\
        --db-url sqlite:///./persona_store.db

    # Restore PostgreSQL
    python scripts/restore.py \\
        --backup /tmp/backups/persona_backup_20240101T020000Z.sql.gz \\
        --db-url postgresql://user:pass@localhost/persona

    # Download from S3 then restore
    python scripts/restore.py \\
        --s3-bucket my-bucket \\
        --s3-key backups/persona_backup_20240101T020000Z.sql.gz \\
        --db-url postgresql://user:pass@localhost/persona

    # List available backups
    python scripts/restore.py --list --output /tmp/backups

    # Dry-run (validate backup without restoring)
    python scripts/restore.py \\
        --backup /tmp/backups/backup.db.gz \\
        --db-url sqlite:///./persona_store.db \\
        --dry-run
"""

import argparse
import gzip
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("persona.restore")


def _add_file_handler(log_file: str) -> None:
    """Optionally persist logs to a file (set LOG_FILE env var)."""
    try:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
        logging.getLogger().addHandler(fh)
    except OSError as exc:
        log.warning("Cannot open log file %s: %s", log_file, exc)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_backup_file(backup_file: str) -> None:
    """
    Verify that *backup_file* exists and passes gzip integrity check.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError:      If gzip integrity check fails.
    """
    path = Path(backup_file)
    if not path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    if not path.name.endswith(".gz"):
        raise ValueError(f"Expected a .gz backup file, got: {path.name}")

    size_mb = path.stat().st_size / (1024 * 1024)
    log.info("Backup file: %s (%.2f MB)", path.name, size_mb)

    # Gzip integrity check
    log.info("Validating gzip integrity …")
    try:
        with gzip.open(backup_file, "rb") as gz:
            # Read in chunks to avoid loading the whole file into memory
            chunk_size = 4 * 1024 * 1024  # 4 MB
            total_bytes = 0
            while True:
                chunk = gz.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
        log.info("Gzip integrity OK — uncompressed size: %.2f MB", total_bytes / (1024 * 1024))
    except (gzip.BadGzipFile, OSError) as exc:
        raise RuntimeError(f"Backup file is corrupted (gzip check failed): {exc}") from exc


# ---------------------------------------------------------------------------
# SQLite restore
# ---------------------------------------------------------------------------

def restore_sqlite(backup_file: str, target_path: str, *, dry_run: bool = False) -> str:
    """
    Decompress *backup_file* (a ``.db.gz``) and write the SQLite database to
    *target_path*.

    The function creates a timestamped safety copy of an existing database at
    *target_path* before overwriting it.

    Args:
        backup_file: Path to the ``.db.gz`` backup produced by backup_sqlite().
        target_path: Destination path for the restored database file.
                     If it contains a SQLAlchemy URL prefix (``sqlite:///``),
                     that prefix is stripped automatically.
        dry_run:     If True, validate the backup but do not write any files.

    Returns:
        Resolved path of the restored database file.

    Raises:
        FileNotFoundError: If the backup file does not exist.
        RuntimeError:      On I/O failure or gzip corruption.
    """
    validate_backup_file(backup_file)

    # Strip SQLAlchemy URL prefix if the caller passed a full URL
    raw = target_path.replace("sqlite:///", "", 1)
    if not raw:
        raw = "persona_store.db"
    dest = Path(raw).resolve()

    if dry_run:
        log.info("[DRY-RUN] Would restore %s -> %s", backup_file, dest)
        return str(dest)

    # Safety: back up existing DB before overwriting
    if dest.exists():
        safety_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safety_copy = dest.with_name(f"{dest.stem}_pre_restore_{safety_ts}{dest.suffix}")
        log.info("Safety copy of existing DB: %s", safety_copy)
        shutil.copy2(dest, safety_copy)

    dest.parent.mkdir(parents=True, exist_ok=True)

    log.info("Restoring SQLite: %s -> %s", backup_file, dest)
    try:
        with gzip.open(backup_file, "rb") as gz_in, open(dest, "wb") as out:
            shutil.copyfileobj(gz_in, out)
    except (gzip.BadGzipFile, OSError) as exc:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"SQLite restore I/O error: {exc}") from exc

    size_mb = dest.stat().st_size / (1024 * 1024)
    log.info("SQLite restore complete: %s (%.2f MB)", dest, size_mb)
    return str(dest)


# ---------------------------------------------------------------------------
# PostgreSQL restore
# ---------------------------------------------------------------------------

def restore_postgres(
    backup_file: str,
    database_url: str,
    *,
    create_db: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Decompress *backup_file* (a ``.sql.gz``) and pipe it into ``psql`` to
    restore a PostgreSQL database.

    WARNING: This operation drops and recreates all objects defined in the
    dump.  Run against a fresh / empty database or after a manual DROP to
    avoid conflicts.  A ``--clean`` flag is intentionally NOT added here to
    give the operator explicit control; use ``psql -c 'DROP DATABASE ...'``
    followed by ``psql -c 'CREATE DATABASE ...'`` before calling this if a
    clean slate is required.

    Args:
        backup_file:  Path to the ``.sql.gz`` backup.
        database_url: Target PostgreSQL DSN.
        create_db:    If True, attempt to create the database before restoring
                      (connects to the ``postgres`` maintenance DB).
        dry_run:      Validate backup and print psql command without executing.

    Raises:
        FileNotFoundError: If ``psql`` is not on PATH or backup file missing.
        RuntimeError:      If psql exits non-zero.
    """
    if not shutil.which("psql"):
        raise FileNotFoundError("psql not found on PATH. Install postgresql-client.")

    validate_backup_file(backup_file)

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/") or "persona"
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)
    user = parsed.username or "postgres"

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    # Optionally create the target database first
    if create_db and not dry_run:
        _create_postgres_db(db_name, host, port, user, env)

    psql_cmd = [
        "psql",
        "--host", host,
        "--port", port,
        "--username", user,
        "--dbname", db_name,
        "--no-password",
        "--set", "ON_ERROR_STOP=1",
    ]

    if dry_run:
        log.info("[DRY-RUN] Would run: %s < gunzip(%s)", " ".join(psql_cmd), backup_file)
        return

    log.info("Restoring PostgreSQL: %s -> %s@%s/%s", backup_file, user, host, db_name)

    try:
        with gzip.open(backup_file, "rb") as gz_in:
            sql_data = gz_in.read()
    except (gzip.BadGzipFile, OSError) as exc:
        raise RuntimeError(f"Failed to decompress backup: {exc}") from exc

    log.debug("Decompressed backup: %.2f MB — piping into psql …", len(sql_data) / (1024 * 1024))

    proc = subprocess.run(
        psql_cmd,
        input=sql_data,
        capture_output=True,
        env=env,
    )

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"psql restore exited with code {proc.returncode}:\n{stderr}"
        )

    log.info("PostgreSQL restore complete: %s", db_name)


def _create_postgres_db(
    db_name: str,
    host: str,
    port: str,
    user: str,
    env: dict,
) -> None:
    """
    Attempt to create *db_name* on the target PostgreSQL server.
    Connects to the maintenance ``postgres`` database.  Ignores
    "database already exists" errors.
    """
    cmd = [
        "psql",
        "--host", host,
        "--port", port,
        "--username", user,
        "--dbname", "postgres",
        "--no-password",
        "--command", f"CREATE DATABASE {db_name};",
    ]
    log.info("Attempting to create database %r …", db_name)
    proc = subprocess.run(cmd, capture_output=True, env=env)
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        if "already exists" in stderr:
            log.info("Database %r already exists — continuing.", db_name)
        else:
            raise RuntimeError(f"CREATE DATABASE failed:\n{stderr}")


# ---------------------------------------------------------------------------
# S3 download
# ---------------------------------------------------------------------------

def download_from_s3(bucket: str, key: str, local_path: str) -> str:
    """
    Download ``s3://bucket/key`` to *local_path*.

    Args:
        bucket:     S3 bucket name.
        key:        Object key (path) inside the bucket.
        local_path: Local destination path.

    Returns:
        Resolved local path string.

    Raises:
        RuntimeError: If boto3 is not installed or download fails.
    """
    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    except ImportError:
        raise RuntimeError(
            "boto3 not installed. Run: pip install boto3"
        )

    dest = Path(local_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    log.info("Downloading s3://%s/%s -> %s", bucket, key, dest)

    s3 = boto3.client("s3")
    try:
        s3.download_file(bucket, key, str(dest))
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 download failed: {exc}") from exc

    size_mb = dest.stat().st_size / (1024 * 1024)
    log.info("Download complete: %s (%.2f MB)", dest, size_mb)
    return str(dest)


def list_s3_backups(bucket: str, prefix: str = "") -> list[dict]:
    """
    List backup objects in an S3 bucket.

    Returns a list of dicts with keys: key, size_mb, last_modified.
    """
    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    except ImportError:
        raise RuntimeError("boto3 not installed. Run: pip install boto3")

    s3 = boto3.client("s3")
    backups = []
    paginator = s3.get_paginator("list_objects_v2")

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".db.gz") or key.endswith(".sql.gz"):
                    backups.append(
                        {
                            "key": key,
                            "size_mb": round(obj["Size"] / (1024 * 1024), 2),
                            "last_modified": obj["LastModified"].strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                        }
                    )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 list failed: {exc}") from exc

    backups.sort(key=lambda x: x["last_modified"], reverse=True)
    return backups


# ---------------------------------------------------------------------------
# List local backups (re-used from backup.py for convenience)
# ---------------------------------------------------------------------------

def list_local_backups(output_dir: str) -> list[dict]:
    """Return a list of local backup files sorted newest-first."""
    output_path = Path(output_dir)
    if not output_path.is_dir():
        log.warning("Backup directory not found: %s", output_dir)
        return []

    backups = []
    for pattern in ("*_backup_*.db.gz", "*_backup_*.sql.gz"):
        for p in output_path.glob(pattern):
            stat = p.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
            backups.append(
                {
                    "name": p.name,
                    "path": str(p.resolve()),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "age_hours": round(age_hours, 1),
                    "mtime": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

    backups.sort(key=lambda x: x["mtime"], reverse=True)
    return backups


# ---------------------------------------------------------------------------
# Orchestration helper
# ---------------------------------------------------------------------------

def run_restore(
    db_url: str,
    backup_file: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
    *,
    create_db: bool = False,
    dry_run: bool = False,
) -> str:
    """
    End-to-end restore: optionally download from S3, then restore the
    appropriate database type based on *db_url*.

    Returns:
        Path of the backup file used for the restore.

    Raises:
        ValueError:   On missing / conflicting arguments.
        RuntimeError: On restore failure.
    """
    import time as _time

    start = _time.monotonic()
    log.info("=== Persona Platform Restore Started ===")
    log.info("Database URL scheme: %s", db_url.split(":")[0])
    if dry_run:
        log.info("DRY-RUN mode — no data will be written.")

    # Resolve backup file: download from S3 if needed
    if backup_file is None:
        if not s3_bucket or not s3_key:
            raise ValueError(
                "Either --backup or both --s3-bucket and --s3-key are required."
            )
        tmp_dir = tempfile.mkdtemp(prefix="persona_restore_")
        local_name = Path(s3_key).name
        backup_file = str(Path(tmp_dir) / local_name)
        download_from_s3(s3_bucket, s3_key, backup_file)

    # Dispatch to the correct restore function
    if db_url.startswith("sqlite"):
        restored_path = restore_sqlite(backup_file, db_url, dry_run=dry_run)
    elif db_url.startswith("postgresql") or db_url.startswith("postgres"):
        restore_postgres(backup_file, db_url, create_db=create_db, dry_run=dry_run)
        restored_path = backup_file
    else:
        raise ValueError(f"Unsupported database URL scheme: {db_url!r}")

    elapsed = _time.monotonic() - start
    log.info("=== Restore Finished in %.1fs ===", elapsed)
    return restored_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persona Platform database restore utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # --- modes ---
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--restore",
        dest="mode",
        action="store_const",
        const="restore",
        default="restore",
        help="Run a restore (default mode)",
    )
    mode.add_argument(
        "--list",
        dest="mode",
        action="store_const",
        const="list",
        help="List local backup files in --output directory",
    )
    mode.add_argument(
        "--list-s3",
        dest="mode",
        action="store_const",
        const="list_s3",
        help="List backup objects in --s3-bucket",
    )
    mode.add_argument(
        "--validate",
        dest="mode",
        action="store_const",
        const="validate",
        help="Validate a backup file without restoring",
    )

    # --- restore args ---
    parser.add_argument(
        "--backup",
        default=None,
        help="Path to a local .db.gz or .sql.gz backup file",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./persona_store.db"),
        dest="db_url",
        help="Target SQLAlchemy database URL (default: $DATABASE_URL)",
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        dest="create_db",
        help="(Postgres only) Create the target database if it does not exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Validate the backup but do not write any data",
    )

    # --- S3 args ---
    parser.add_argument(
        "--s3-bucket",
        default=os.getenv("S3_BACKUP_BUCKET", ""),
        dest="s3_bucket",
        help="S3 bucket for download (default: $S3_BACKUP_BUCKET)",
    )
    parser.add_argument(
        "--s3-key",
        default="",
        dest="s3_key",
        help="S3 object key to download",
    )
    parser.add_argument(
        "--s3-prefix",
        default="",
        dest="s3_prefix",
        help="S3 prefix filter when listing (default: none)",
    )

    # --- listing args ---
    parser.add_argument(
        "--output",
        default=os.getenv("BACKUP_DIR", "/tmp/persona_backups"),
        help="Local backup directory for --list (default: /tmp/persona_backups or $BACKUP_DIR)",
    )

    # --- logging ---
    parser.add_argument(
        "--log-file",
        default=os.getenv("LOG_FILE", ""),
        dest="log_file",
        help="Optional path to a log file (in addition to stdout)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.log_file:
        _add_file_handler(args.log_file)

    try:
        if args.mode == "list":
            items = list_local_backups(args.output)
            if not items:
                print(f"No backups found in: {args.output}")
                return 0
            print(f"\nBackups in {args.output}:")
            print(f"{'Name':<55} {'Size (MB)':>10} {'Age (h)':>9}  Timestamp")
            print("-" * 95)
            for b in items:
                print(
                    f"{b['name']:<55} {b['size_mb']:>10.2f} {b['age_hours']:>9.1f}  {b['mtime']}"
                )
            print(f"\nTotal: {len(items)} backup(s)")

        elif args.mode == "list_s3":
            if not args.s3_bucket:
                log.error("--s3-bucket is required for --list-s3")
                return 1
            items = list_s3_backups(args.s3_bucket, prefix=args.s3_prefix)
            if not items:
                print(f"No backups found in s3://{args.s3_bucket}/{args.s3_prefix}")
                return 0
            print(f"\nBackups in s3://{args.s3_bucket}/{args.s3_prefix}:")
            print(f"{'Key':<70} {'Size (MB)':>10}  Last Modified")
            print("-" * 100)
            for b in items:
                print(f"{b['key']:<70} {b['size_mb']:>10.2f}  {b['last_modified']}")
            print(f"\nTotal: {len(items)} backup(s)")

        elif args.mode == "validate":
            if not args.backup:
                log.error("--backup is required for --validate")
                return 1
            validate_backup_file(args.backup)
            print(f"Backup file is valid: {args.backup}")

        else:  # "restore"
            restored = run_restore(
                db_url=args.db_url,
                backup_file=args.backup or None,
                s3_bucket=args.s3_bucket or None,
                s3_key=args.s3_key or None,
                create_db=args.create_db,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                print(f"[DRY-RUN] Restore validated. Backup: {restored}")
            else:
                print(f"Restore complete. Source backup: {restored}")

    except KeyboardInterrupt:
        log.warning("Restore interrupted by user.")
        return 130
    except Exception as exc:
        log.error("Restore failed: %s", exc, exc_info=args.verbose)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

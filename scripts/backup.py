#!/usr/bin/env python3
"""
Persona Platform — Automated Database Backup Script

Supports SQLite (dev) and PostgreSQL (production).
Optionally uploads completed backups to S3 and enforces retention policies.

Usage:
    python scripts/backup.py --output /tmp/backups --db-url $DATABASE_URL
    python scripts/backup.py --output /tmp/backups --db-url $DATABASE_URL --s3-bucket my-bucket
    python scripts/backup.py --list --output /tmp/backups
    python scripts/backup.py --cleanup --output /tmp/backups --keep-days 30
"""

import argparse
import gzip
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
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
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("persona.backup")


def _add_file_handler(log_file: str) -> None:
    """Optionally persist logs to a file (set LOG_FILE env var)."""
    try:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
        logging.getLogger().addHandler(fh)
    except OSError as exc:
        log.warning("Cannot open log file %s: %s", log_file, exc)


# ---------------------------------------------------------------------------
# SQLite backup
# ---------------------------------------------------------------------------

def backup_sqlite(output_dir: str, db_url: str) -> str:
    """
    Copy the SQLite database file to *output_dir* with a UTC timestamp suffix,
    then gzip-compress it.

    Args:
        output_dir: Directory where the backup will be written.
        db_url:     SQLAlchemy URL like ``sqlite:///./persona_store.db``
                    or ``sqlite:////absolute/path/persona_store.db``.

    Returns:
        Absolute path of the produced ``.db.gz`` file.

    Raises:
        FileNotFoundError: If the source database file does not exist.
        RuntimeError:      On any I/O failure.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract file path from URL: strip ``sqlite:///`` (3 slashes = relative,
    # 4 slashes = absolute on Unix).
    raw_path = db_url.replace("sqlite:///", "", 1)
    if not raw_path:
        raw_path = "persona_store.db"
    db_file = Path(raw_path).resolve()

    if not db_file.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_file}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = db_file.stem  # e.g. "persona_store"
    backup_name = f"{base_name}_backup_{timestamp}.db.gz"
    backup_path = output_path / backup_name

    log.info("Starting SQLite backup: %s -> %s", db_file, backup_path)

    try:
        with open(db_file, "rb") as src, gzip.open(backup_path, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst)
    except OSError as exc:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError(f"SQLite backup I/O error: {exc}") from exc

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    log.info("SQLite backup complete: %s (%.2f MB)", backup_path, size_mb)
    return str(backup_path)


# ---------------------------------------------------------------------------
# PostgreSQL backup
# ---------------------------------------------------------------------------

def backup_postgres(database_url: str, output_dir: str) -> str:
    """
    Run ``pg_dump`` against *database_url*, piping output through gzip.

    Args:
        database_url: Standard PostgreSQL DSN, e.g.
                      ``postgresql://user:pass@host:5432/dbname``.
        output_dir:   Directory where the ``.sql.gz`` file will be written.

    Returns:
        Absolute path of the produced ``.sql.gz`` file.

    Raises:
        FileNotFoundError: If ``pg_dump`` is not on PATH.
        RuntimeError:      If pg_dump exits non-zero or I/O fails.
    """
    if not shutil.which("pg_dump"):
        raise FileNotFoundError("pg_dump not found on PATH. Install postgresql-client.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/") or "persona"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{db_name}_backup_{timestamp}.sql.gz"
    backup_path = output_path / backup_name

    log.info("Starting PostgreSQL backup: %s -> %s", database_url.split("@")[-1], backup_path)

    # Build environment with PGPASSWORD so pg_dump won't prompt.
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_dump",
        "--host", parsed.hostname or "localhost",
        "--port", str(parsed.port or 5432),
        "--username", parsed.username or "postgres",
        "--dbname", db_name,
        "--format", "plain",
        "--no-password",
        "--verbose",
    ]

    log.debug("pg_dump command: %s", " ".join(cmd))

    try:
        with gzip.open(backup_path, "wb", compresslevel=6) as gz_out:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            stdout, stderr = proc.communicate()

            if proc.returncode != 0:
                backup_path.unlink(missing_ok=True)
                err_text = stderr.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"pg_dump exited with code {proc.returncode}:\n{err_text}"
                )

            gz_out.write(stdout)
    except OSError as exc:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError(f"PostgreSQL backup I/O error: {exc}") from exc

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    log.info("PostgreSQL backup complete: %s (%.2f MB)", backup_path, size_mb)
    return str(backup_path)


# ---------------------------------------------------------------------------
# S3 upload / download
# ---------------------------------------------------------------------------

def upload_to_s3(
    file_path: str,
    bucket: str,
    key: str,
    *,
    sse: str = "AES256",
) -> bool:
    """
    Upload *file_path* to ``s3://bucket/key`` using boto3.

    The function is a no-op (returns False) when *bucket* is empty or boto3 is
    not installed, so callers can treat S3 as optional.

    Args:
        file_path: Local file to upload.
        bucket:    S3 bucket name.
        key:       Destination key (path) inside the bucket.
        sse:       Server-side encryption algorithm (default ``AES256``).

    Returns:
        True on success, False when skipped or on non-fatal misconfiguration.

    Raises:
        RuntimeError: On boto3 upload error.
    """
    if not bucket:
        log.debug("S3_BACKUP_BUCKET not set — skipping S3 upload.")
        return False

    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    except ImportError:
        log.warning("boto3 not installed — skipping S3 upload. Run: pip install boto3")
        return False

    src = Path(file_path)
    if not src.exists():
        raise RuntimeError(f"File to upload not found: {file_path}")

    size_mb = src.stat().st_size / (1024 * 1024)
    log.info("Uploading to s3://%s/%s (%.2f MB) …", bucket, key, size_mb)

    s3 = boto3.client("s3")
    try:
        s3.upload_file(
            str(src),
            bucket,
            key,
            ExtraArgs={"ServerSideEncryption": sse},
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 upload failed: {exc}") from exc

    log.info("S3 upload complete: s3://%s/%s", bucket, key)
    return True


def download_from_s3(bucket: str, key: str, local_path: str) -> str:
    """
    Download ``s3://bucket/key`` to *local_path*.

    Returns:
        The resolved local path as a string.

    Raises:
        RuntimeError: On boto3 download error or missing boto3.
    """
    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    except ImportError:
        raise RuntimeError("boto3 not installed. Run: pip install boto3")

    dest = Path(local_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    log.info("Downloading s3://%s/%s -> %s", bucket, key, dest)

    s3 = boto3.client("s3")
    try:
        s3.download_file(bucket, key, str(dest))
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 download failed: {exc}") from exc

    log.info("Download complete: %s", dest)
    return str(dest)


# ---------------------------------------------------------------------------
# Backup listing
# ---------------------------------------------------------------------------

def list_backups(output_dir: str) -> list[dict]:
    """
    Return a list of backup files in *output_dir*, sorted newest-first.

    Each dict contains:
        name      – filename
        path      – absolute path string
        size_mb   – file size in megabytes (float)
        age_hours – age in hours relative to now (float)
        mtime     – ISO-8601 UTC modification timestamp
    """
    output_path = Path(output_dir)
    if not output_path.is_dir():
        log.warning("Backup directory not found: %s", output_dir)
        return []

    backups = []
    patterns = ("*_backup_*.db.gz", "*_backup_*.sql.gz")
    seen: set[str] = set()

    for pattern in patterns:
        for p in output_path.glob(pattern):
            if p.name in seen:
                continue
            seen.add(p.name)
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


def print_backups(output_dir: str) -> None:
    """Pretty-print the backup listing to stdout."""
    items = list_backups(output_dir)
    if not items:
        print(f"No backups found in: {output_dir}")
        return

    print(f"\nBackups in {output_dir}:")
    print(f"{'Name':<55} {'Size (MB)':>10} {'Age (h)':>9}  Timestamp")
    print("-" * 95)
    for b in items:
        print(
            f"{b['name']:<55} {b['size_mb']:>10.2f} {b['age_hours']:>9.1f}  {b['mtime']}"
        )
    print(f"\nTotal: {len(items)} backup(s)")


# ---------------------------------------------------------------------------
# Cleanup old backups
# ---------------------------------------------------------------------------

def cleanup_old_backups(output_dir: str, keep_days: int = 30) -> list[str]:
    """
    Delete backup files in *output_dir* that are older than *keep_days* days.

    Returns:
        List of deleted file paths.
    """
    output_path = Path(output_dir)
    if not output_path.is_dir():
        log.warning("Backup directory not found: %s — nothing to clean.", output_dir)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    deleted: list[str] = []

    for pattern in ("*_backup_*.db.gz", "*_backup_*.sql.gz"):
        for p in output_path.glob(pattern):
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                log.info("Deleting old backup: %s (age %.0f days)", p.name, (datetime.now(timezone.utc) - mtime).days)
                p.unlink()
                deleted.append(str(p))

    if deleted:
        log.info("Cleanup complete: %d file(s) deleted.", len(deleted))
    else:
        log.info("Cleanup: no backups older than %d days.", keep_days)

    return deleted


# ---------------------------------------------------------------------------
# Orchestration helper
# ---------------------------------------------------------------------------

def run_backup(
    db_url: str,
    output_dir: str,
    s3_bucket: Optional[str] = None,
    keep_days: int = 30,
) -> str:
    """
    End-to-end backup: detect DB type, run backup, optionally upload to S3,
    and clean up old local backups.

    Returns:
        Path of the produced backup file.
    """
    start = time.monotonic()
    log.info("=== Persona Platform Backup Started ===")
    log.info("Database URL scheme: %s", db_url.split(":")[0])
    log.info("Output directory   : %s", output_dir)

    if db_url.startswith("sqlite"):
        backup_file = backup_sqlite(output_dir, db_url)
    elif db_url.startswith("postgresql") or db_url.startswith("postgres"):
        backup_file = backup_postgres(db_url, output_dir)
    else:
        raise ValueError(f"Unsupported database URL scheme: {db_url!r}")

    # S3 upload (optional)
    effective_bucket = s3_bucket or os.getenv("S3_BACKUP_BUCKET", "")
    if effective_bucket:
        s3_key = Path(backup_file).name
        upload_to_s3(backup_file, effective_bucket, s3_key)

    # Retention cleanup
    cleanup_old_backups(output_dir, keep_days=keep_days)

    elapsed = time.monotonic() - start
    log.info("=== Backup Finished in %.1fs ===", elapsed)
    return backup_file


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persona Platform database backup utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--backup",
        dest="mode",
        action="store_const",
        const="backup",
        default="backup",
        help="Run a backup (default mode)",
    )
    mode.add_argument(
        "--list",
        dest="mode",
        action="store_const",
        const="list",
        help="List existing backups in --output directory",
    )
    mode.add_argument(
        "--cleanup",
        dest="mode",
        action="store_const",
        const="cleanup",
        help="Delete backups older than --keep-days",
    )

    parser.add_argument(
        "--output",
        default=os.getenv("BACKUP_DIR", "/tmp/persona_backups"),
        help="Directory for backup files (default: /tmp/persona_backups or $BACKUP_DIR)",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./persona_store.db"),
        dest="db_url",
        help="SQLAlchemy database URL (default: $DATABASE_URL or sqlite dev path)",
    )
    parser.add_argument(
        "--s3-bucket",
        default=os.getenv("S3_BACKUP_BUCKET", ""),
        dest="s3_bucket",
        help="S3 bucket name for upload (default: $S3_BACKUP_BUCKET)",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
        dest="keep_days",
        help="Days of backups to retain (default: 30 or $BACKUP_RETENTION_DAYS)",
    )
    parser.add_argument(
        "--log-file",
        default=os.getenv("LOG_FILE", ""),
        dest="log_file",
        help="Optional path to a log file (additionally to stdout)",
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
            print_backups(args.output)

        elif args.mode == "cleanup":
            deleted = cleanup_old_backups(args.output, keep_days=args.keep_days)
            print(f"Deleted {len(deleted)} backup(s) older than {args.keep_days} days.")

        else:  # "backup"
            backup_file = run_backup(
                db_url=args.db_url,
                output_dir=args.output,
                s3_bucket=args.s3_bucket or None,
                keep_days=args.keep_days,
            )
            print(f"Backup created: {backup_file}")

    except KeyboardInterrupt:
        log.warning("Backup interrupted by user.")
        return 130
    except Exception as exc:
        log.error("Backup failed: %s", exc, exc_info=args.verbose)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

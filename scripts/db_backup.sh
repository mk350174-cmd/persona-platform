#!/usr/bin/env bash
# Database backup (T2-045). Supports the two DATABASE_URL forms api/db.py
# accepts: sqlite:///<path> (dev default) and postgresql://... (production,
# ADR 0001). Writes a timestamped dump to $BACKUP_DIR (default ./backups).
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-sqlite:///./persona_platform.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"

if [[ "$DATABASE_URL" == sqlite:///* ]]; then
    DB_PATH="${DATABASE_URL#sqlite:///}"
    if [[ ! -f "$DB_PATH" ]]; then
        echo "error: sqlite db not found at $DB_PATH" >&2
        exit 1
    fi
    OUT="$BACKUP_DIR/persona_platform_${TIMESTAMP}.db"
    # sqlite3's own online-backup API (via Python stdlib) rather than the
    # sqlite3 CLI binary, which isn't guaranteed present in every image.
    python3 -c "
import sqlite3
src = sqlite3.connect('$DB_PATH')
dst = sqlite3.connect('$OUT')
src.backup(dst)
dst.close()
src.close()
"
    echo "backup written: $OUT"

elif [[ "$DATABASE_URL" == postgresql://* || "$DATABASE_URL" == postgres://* ]]; then
    OUT="$BACKUP_DIR/persona_platform_${TIMESTAMP}.sql.gz"
    pg_dump --dbname="$DATABASE_URL" --format=plain --no-owner | gzip > "$OUT"
    echo "backup written: $OUT"

else
    echo "error: unrecognized DATABASE_URL scheme: $DATABASE_URL" >&2
    exit 1
fi

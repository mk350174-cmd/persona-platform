#!/usr/bin/env bash
# Database restore (T2-045). Counterpart to db_backup.sh. Usage:
#   ./scripts/db_restore.sh <backup-file>
# Refuses to run without an explicit CONFIRM=yes — restoring overwrites the
# current database.
set -euo pipefail

BACKUP_FILE="${1:?usage: db_restore.sh <backup-file>}"
DATABASE_URL="${DATABASE_URL:-sqlite:///./persona_platform.db}"

if [[ "${CONFIRM:-}" != "yes" ]]; then
    echo "error: this overwrites the current database. Re-run with CONFIRM=yes." >&2
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "error: backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

if [[ "$DATABASE_URL" == sqlite:///* ]]; then
    DB_PATH="${DATABASE_URL#sqlite:///}"
    cp "$BACKUP_FILE" "$DB_PATH"
    echo "restored sqlite db from $BACKUP_FILE to $DB_PATH"

elif [[ "$DATABASE_URL" == postgresql://* || "$DATABASE_URL" == postgres://* ]]; then
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" | psql --dbname="$DATABASE_URL"
    else
        psql --dbname="$DATABASE_URL" -f "$BACKUP_FILE"
    fi
    echo "restored postgres db from $BACKUP_FILE"

else
    echo "error: unrecognized DATABASE_URL scheme: $DATABASE_URL" >&2
    exit 1
fi

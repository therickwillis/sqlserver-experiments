#!/usr/bin/env bash
set -euo pipefail

# wait-for-sqlserver.sh
# Waits for SQL Server to be ready before proceeding.
# Uses environment variables: DB_SERVER, DB_PORT, DB_USER, DB_PASSWORD.

DB_SERVER="${DB_SERVER:-sqlserver}"
DB_PORT="${DB_PORT:-1433}"
DB_USER="${DB_USER:-sa}"
DB_PASSWORD="${DB_PASSWORD:-}"

MAX_ATTEMPTS="${MAX_ATTEMPTS:-60}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

if [ -z "${DB_PASSWORD}" ]; then
  echo "ERROR: DB_PASSWORD environment variable is not set."
  exit 1
fi

# Build connection string
TARGET_SERVER="$DB_SERVER"
if [ -n "$DB_PORT" ] && [[ "$DB_SERVER" != *,* ]]; then
  TARGET_SERVER="${DB_SERVER},${DB_PORT}"
fi

echo "Waiting for SQL Server at ${TARGET_SERVER} to be ready (max ${MAX_ATTEMPTS} attempts)..."

for i in $(seq 1 $MAX_ATTEMPTS); do
  if sqlcmd -S "$TARGET_SERVER" -U "$DB_USER" -P "$DB_PASSWORD" -C -Q "SELECT 1" > /dev/null 2>&1; then
    echo "SQL Server is ready!"
    exit 0
  fi
  echo "Attempt $i/$MAX_ATTEMPTS: SQL Server not ready yet, waiting ${SLEEP_SECONDS}s..."
  sleep $SLEEP_SECONDS
done

echo "ERROR: SQL Server did not become ready after ${MAX_ATTEMPTS} attempts."
exit 2

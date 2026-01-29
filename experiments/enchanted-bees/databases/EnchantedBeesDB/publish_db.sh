#!/usr/bin/env bash
set -euo pipefail

# publish_db.sh
# Publishes the EnchantedBeesDB DACPAC using sqlpackage.
# Uses environment variables: DB_SERVER, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
# Optional: DACPAC (path) and SQLPACKAGE_PATH (absolute path to sqlpackage).

DB_SERVER="${DB_SERVER:-sqlserver}"
DB_PORT="${DB_PORT:-1433}"
DB_USER="${DB_USER:-sa}"
DB_PASSWORD="${DB_PASSWORD:-}" # required
DB_NAME="${DB_NAME:-EnchantedBeesDB}"
PROJECT="${PROJECT:-$(dirname "$0")/EnchantedBeesDB.sqlproj}"
CONFIGURATION="${CONFIGURATION:-Debug}"

usage() {
  cat <<EOF
Usage: DB_PASSWORD must be set in environment.
Optional env vars: DB_SERVER (default sqlserver), DB_PORT (default 1433), DB_USER (default sa), DB_NAME (default EnchantedBeesDB), PROJECT, CONFIGURATION
Example:
  DB_SERVER=host.docker.internal DB_PASSWORD=YourPass ./EnchantedBeesDB/publish_db.sh
EOF
}

if [ -z "${DB_PASSWORD}" ]; then
  echo "ERROR: DB_PASSWORD environment variable is not set."
  usage
  exit 2
fi

if [ ! -f "$PROJECT" ]; then
  echo "ERROR: sqlproj not found at $PROJECT"
  echo "Set PROJECT env var to point to your .sqlproj file if different."
  exit 3
fi

# Build target server string (append port if server doesn't already include one)
TARGET_SERVER="$DB_SERVER"
if [ -n "$DB_PORT" ] && [[ "$DB_SERVER" != *,* ]]; then
  TARGET_SERVER="${DB_SERVER},${DB_PORT}"
fi

CONN="Data Source=${TARGET_SERVER};Initial Catalog=${DB_NAME};User ID=${DB_USER};Password=${DB_PASSWORD};Encrypt=True;Trust Server Certificate=True;"

# Ensure dotnet is available
if ! command -v dotnet >/dev/null 2>&1; then
  echo "ERROR: dotnet CLI not found in PATH."
  exit 4
fi

echo "Building project $PROJECT (configuration=$CONFIGURATION) to produce dacpac..."
dotnet build "$PROJECT" -c "$CONFIGURATION"

# Determine DACPAC path
DACPAC_PATH="${DACPAC:-$(dirname "$PROJECT")/bin/${CONFIGURATION}/EnchantedBeesDB.dacpac}"

if [ ! -f "$DACPAC_PATH" ]; then
  echo "ERROR: DACPAC not found at $DACPAC_PATH"
  exit 5
fi

# Ensure sqlpackage is available
if ! command -v sqlpackage >/dev/null 2>&1; then
  echo "sqlpackage not found. Installing Microsoft.SqlPackage as a dotnet tool..."
  dotnet tool install -g microsoft.sqlpackage || {
    echo "ERROR: Failed to install sqlpackage"
    exit 6
  }
  # Add dotnet tools to PATH if not already there
  export PATH="$PATH:$HOME/.dotnet/tools"
fi

echo "Publishing DACPAC to ${TARGET_SERVER}/${DB_NAME} (user=$DB_USER) using sqlpackage..."
sqlpackage /Action:Publish \
  /SourceFile:"$DACPAC_PATH" \
  /TargetServerName:"$TARGET_SERVER" \
  /TargetDatabaseName:"$DB_NAME" \
  /TargetUser:"$DB_USER" \
  /TargetPassword:"$DB_PASSWORD" \
  /TargetEncryptConnection:True \
  /TargetTrustServerCertificate:True \
  /p:DropObjectsNotInSource=True \
  /p:AllowIncompatiblePlatform=True

echo "Publish finished."

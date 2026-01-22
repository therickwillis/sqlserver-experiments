#!/bin/bash
set -euo pipefail

# dev-entrypoint.sh
# If DEV_MODE=1 and a mounted workspace contains src/requirements.txt,
# install into the user site (`--user`) so developers can iterate without
# rebuilding the image. Otherwise, start the provided command.

DEV_MODE=${DEV_MODE:-0}

if [ "${DEV_MODE}" = "1" ]; then
  if [ -f /workspace/src/requirements.txt ]; then
    echo "DEV_MODE=1: installing /workspace/src/requirements.txt into user site"
    python3 -m pip install --user --upgrade pip setuptools wheel
    python3 -m pip install --user -r /workspace/src/requirements.txt
  else
    echo "DEV_MODE=1 but /workspace/src/requirements.txt not found"
  fi

  # Auto-publish database on startup
  if [ -f /workspace/EnchantedBeesDB/publish_db.sh ]; then
    echo "DEV_MODE=1: waiting 60 seconds for SQL Server, then publishing database..."
    sleep 60
    /workspace/EnchantedBeesDB/publish_db.sh
  fi
fi

exec "$@"

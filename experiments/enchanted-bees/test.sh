#!/bin/bash
# Wrapper script to run test suite in container

echo "Running migration test suite in dev container..."
echo

MSYS_NO_PATHCONV=1 docker compose exec dev /workspace/test-migrations.sh

exit $?

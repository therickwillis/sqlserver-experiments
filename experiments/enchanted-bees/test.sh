#!/bin/bash
# Wrapper script to run all test suites in container

echo "Running test suites in dev container..."
echo

# Run migration tests
echo "============================================================"
echo "  Running Migration Tests"
echo "============================================================"
echo
MSYS_NO_PATHCONV=1 docker compose exec dev /workspace/test-migrations.sh
MIGRATION_EXIT=$?

echo
echo

# Run drift detection tests
echo "============================================================"
echo "  Running Drift Detection Tests"
echo "============================================================"
echo
MSYS_NO_PATHCONV=1 docker compose exec dev /workspace/test-drift.sh
DRIFT_EXIT=$?

echo
echo

# Summary
echo "============================================================"
echo "  Test Suite Summary"
echo "============================================================"
echo

if [ $MIGRATION_EXIT -eq 0 ]; then
    echo "✓ Migration Tests: PASSED"
else
    echo "✗ Migration Tests: FAILED (exit code $MIGRATION_EXIT)"
fi

if [ $DRIFT_EXIT -eq 0 ]; then
    echo "✓ Drift Detection Tests: PASSED"
else
    echo "✗ Drift Detection Tests: FAILED (exit code $DRIFT_EXIT)"
fi

echo

# Exit with failure if any test suite failed
if [ $MIGRATION_EXIT -ne 0 ] || [ $DRIFT_EXIT -ne 0 ]; then
    echo "Some tests failed"
    exit 1
else
    echo "All tests passed!"
    exit 0
fi

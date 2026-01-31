#!/bin/bash
# Drift Detection Test Suite
# Tests Epic 4: Environment Drift Detection

# Note: We don't use 'set -e' because we want to continue after test failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_header() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo
}

print_test() {
    echo -e "${BLUE}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${YELLOW}INFO:${NC} $1"
}

# Test: Command succeeds (exit code 0)
assert_command_success() {
    if eval "$1" > /dev/null 2>&1; then
        print_pass "Command succeeded: $1"
        return 0
    else
        print_fail "Command failed: $1"
        return 1
    fi
}

# Test: Command fails (non-zero exit code)
assert_command_fails() {
    if eval "$1" > /dev/null 2>&1; then
        print_fail "Command succeeded (should fail): $1"
        return 1
    else
        print_pass "Command failed as expected: $1"
        return 0
    fi
}

# Test: File exists
assert_file_exists() {
    if [ -f "$1" ]; then
        print_pass "File exists: $1"
        return 0
    else
        print_fail "File does not exist: $1"
        return 1
    fi
}

# Test: File contains string
assert_file_contains() {
    if grep -qF -- "$2" "$1" 2>/dev/null; then
        print_pass "File contains '$2': $1"
        return 0
    else
        print_fail "File does not contain '$2': $1"
        return 1
    fi
}

# Test: Output contains string
assert_output_contains() {
    local output="$1"
    local expected="$2"
    if echo "$output" | grep -qF -- "$expected"; then
        print_pass "Output contains: $expected"
        return 0
    else
        print_fail "Output does not contain: $expected"
        echo "Output was: $output"
        return 1
    fi
}

# Cleanup function
cleanup_test_artifacts() {
    print_info "Cleaning up test artifacts..."

    # Remove test repair migrations
    rm -f /workspace/migrations/EnchantedBeesDB/*repair_schema_drift*

    # Remove any test tables created
    docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "${SA_PASSWORD}" -d EnchantedBeesDB \
        -C -Q "IF OBJECT_ID('dbo.DriftTestTable', 'U') IS NOT NULL DROP TABLE dbo.DriftTestTable" \
        > /dev/null 2>&1

    print_info "Cleanup complete"
}

# Initialize database to clean state
initialize_database() {
    print_info "Initializing database to clean state..."

    # Ensure database exists and is initialized
    PYTHONPATH=/workspace/src python3 -m dbctl.cli init > /dev/null 2>&1

    print_info "Database initialized"
}

# Main test execution
print_header "Epic 4: Environment Drift Detection - Test Suite"
echo

# Get SA password from environment
SA_PASSWORD="${SA_PASSWORD:-YourStrong@Passw0rd}"

# Cleanup before tests
cleanup_test_artifacts
initialize_database

echo
print_header "Test Group 1: Basic Drift Detection"
echo

# Test 1: No drift on clean database
print_test "No drift detected on freshly initialized database"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift 2>&1)
if echo "$OUTPUT" | grep -q "No drift detected"; then
    print_pass "No drift detected on clean database"
else
    print_fail "Expected no drift on clean database"
fi
echo

# Test 2: Drift command returns exit code 0 when no drift
print_test "Drift command returns exit code 0 when no drift"
PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --exit-code > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_pass "Exit code 0 for no drift"
else
    print_fail "Expected exit code 0 for no drift"
fi
echo

# Test 3: Detect drift when extra table exists in database
print_test "Detect drift when extra table exists in database"
# Create an extra table not in project
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P "${SA_PASSWORD}" -d EnchantedBeesDB \
    -C -Q "CREATE TABLE dbo.DriftTestTable (Id INT PRIMARY KEY, Name NVARCHAR(100))" \
    > /dev/null 2>&1

OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift 2>&1)
if echo "$OUTPUT" | grep -q "drift detected"; then
    print_pass "Drift detected with extra table"
else
    print_fail "Expected drift to be detected"
fi
echo

# Test 4: Drift command returns exit code 1 when drift detected
print_test "Drift command returns exit code 1 with --exit-code flag"
PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --exit-code > /dev/null 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 1 ]; then
    print_pass "Exit code 1 for drift detected"
else
    print_fail "Expected exit code 1 for drift, got $EXIT_CODE"
fi
echo

# Test 5: JSON output format
print_test "Drift report in JSON format"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --output json 2>&1)
if echo "$OUTPUT" | grep -q '"has_drift": true'; then
    print_pass "JSON output contains has_drift field"
else
    print_fail "JSON output missing has_drift field"
fi

if echo "$OUTPUT" | grep -q '"drift_count"'; then
    print_pass "JSON output contains drift_count field"
else
    print_fail "JSON output missing drift_count field"
fi
echo

# Test 6: XML output format
print_test "Drift report in XML format"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --output xml 2>&1)
if echo "$OUTPUT" | grep -q "Operation"; then
    print_pass "XML output format works"
else
    print_fail "XML output format failed"
fi
echo

echo
print_header "Test Group 2: Drift Tolerance Levels"
echo

# Test 7: Strict tolerance detects all differences
print_test "Strict tolerance detects all drift"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --tolerance strict 2>&1)
if echo "$OUTPUT" | grep -q "drift detected"; then
    print_pass "Strict tolerance detected drift"
else
    print_fail "Strict tolerance should detect drift"
fi
echo

# Test 8: Normal tolerance (default)
print_test "Normal tolerance uses default settings"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --tolerance normal 2>&1)
if echo "$OUTPUT" | grep -q "tolerance"; then
    print_pass "Normal tolerance accepted"
else
    print_fail "Normal tolerance failed"
fi
echo

echo
print_header "Test Group 3: Repair Migration Generation"
echo

# Test 9: Generate repair migration with --fix flag
print_test "Generate repair migration to fix drift"
PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --fix > /dev/null 2>&1
# Check if repair migration file was created
REPAIR_FILE=$(ls /workspace/migrations/EnchantedBeesDB/*repair_schema_drift.sql 2>/dev/null | head -1)
if [ -n "$REPAIR_FILE" ]; then
    print_pass "Repair migration file created"
else
    print_fail "Repair migration file not created"
fi
echo

# Test 10: Repair migration contains warning headers
print_test "Repair migration contains safety warnings"
if [ -n "$REPAIR_FILE" ]; then
    if grep -q "WARNING" "$REPAIR_FILE"; then
        print_pass "Repair migration contains WARNING"
    else
        print_fail "Repair migration missing WARNING"
    fi

    if grep -q "REVIEW REQUIRED" "$REPAIR_FILE"; then
        print_pass "Repair migration contains REVIEW REQUIRED markers"
    else
        print_fail "Repair migration missing REVIEW REQUIRED markers"
    fi
else
    print_fail "No repair migration file to check"
fi
echo

# Test 11: DOWN migration file created
print_test "DOWN migration file created for repair"
if [ -n "$REPAIR_FILE" ]; then
    DOWN_FILE="${REPAIR_FILE%.sql}.down.sql"
    if [ -f "$DOWN_FILE" ]; then
        print_pass "DOWN migration file created"
    else
        print_fail "DOWN migration file not created"
    fi
else
    print_fail "No repair migration to check for DOWN file"
fi
echo

echo
print_header "Test Group 4: Drift Report Saving"
echo

# Test 12: Save drift report to file
print_test "Save drift report to file"
REPORT_FILE="/tmp/drift-report-test.json"
PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --output json --report-file "$REPORT_FILE" > /dev/null 2>&1
if [ -f "$REPORT_FILE" ]; then
    print_pass "Drift report saved to file"
    rm -f "$REPORT_FILE"
else
    print_fail "Drift report file not created"
fi
echo

echo
print_header "Test Group 5: Dry-Run Mode"
echo

# Test 13: Dry-run mode doesn't connect to database
print_test "Dry-run mode shows what would be checked"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --dry-run 2>&1)
if echo "$OUTPUT" | grep -q "Dry-run"; then
    print_pass "Dry-run mode works"
else
    print_fail "Dry-run mode failed"
fi
echo

echo
print_header "Test Group 6: Migrate Integration"
echo

# Clean up the extra table for clean migration test
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P "${SA_PASSWORD}" -d EnchantedBeesDB \
    -C -Q "IF OBJECT_ID('dbo.DriftTestTable', 'U') IS NOT NULL DROP TABLE dbo.DriftTestTable" \
    > /dev/null 2>&1

# Test 14: Migrate with drift validation (no drift)
print_test "Migrate with --validate-drift when no drift exists"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli migrate --validate-drift --dry-run 2>&1)
if echo "$OUTPUT" | grep -q "No drift"; then
    print_pass "Migrate validates no drift"
else
    print_fail "Migrate drift validation failed"
fi
echo

# Add drift back for next test
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P "${SA_PASSWORD}" -d EnchantedBeesDB \
    -C -Q "CREATE TABLE dbo.DriftTestTable (Id INT PRIMARY KEY, Name NVARCHAR(100))" \
    > /dev/null 2>&1

# Test 15: Migrate blocks when drift detected
print_test "Migrate blocks when drift is detected"
PYTHONPATH=/workspace/src python3 -m dbctl.cli migrate --validate-drift --dry-run > /dev/null 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    print_pass "Migrate blocked due to drift"
else
    print_fail "Migrate should block when drift detected"
fi
echo

# Test 16: Migrate with --force overrides drift check
print_test "Migrate with --force proceeds despite drift"
OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli migrate --validate-drift --force --dry-run 2>&1)
if echo "$OUTPUT" | grep -q "Proceeding with migration despite drift"; then
    print_pass "Migrate --force overrides drift check"
else
    print_fail "Migrate --force should allow migration despite drift"
fi
echo

# Test 17: Drift detection works with baseline DACPAC
print_test "Drift detection with --baseline option"
# First, ensure there's a baseline file
BASELINE_DIR="/workspace/.dbctl/baselines"
mkdir -p "$BASELINE_DIR"
BASELINE_FILE=$(ls "$BASELINE_DIR"/EnchantedBeesDB_*.dacpac 2>/dev/null | head -1)

if [ -n "$BASELINE_FILE" ]; then
    OUTPUT=$(PYTHONPATH=/workspace/src python3 -m dbctl.cli drift --baseline "$BASELINE_FILE" 2>&1)
    if [ $? -eq 0 ]; then
        print_pass "Drift detection with baseline DACPAC works"
    else
        print_fail "Drift detection with baseline DACPAC failed"
    fi
else
    print_info "No baseline DACPAC found, skipping baseline test"
fi
echo

# Final cleanup
cleanup_test_artifacts

# Test summary
echo
print_header "Test Summary"
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo -e "${BLUE}Total:${NC}  $((TESTS_PASSED + TESTS_FAILED))"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

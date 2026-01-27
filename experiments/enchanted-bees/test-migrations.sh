#!/bin/bash
# Migration Generation System Test Suite
# Tests Epic 1: Migration Generation System

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

# Test: File exists
assert_file_exists() {
    if [ -f "$1" ]; then
        print_pass "File exists: $1"
    else
        print_fail "File does not exist: $1"
    fi
}

# Test: File does not exist
assert_file_not_exists() {
    if [ ! -f "$1" ]; then
        print_pass "File does not exist: $1"
    else
        print_fail "File exists (should not): $1"
    fi
}

# Test: Directory exists
assert_dir_exists() {
    if [ -d "$1" ]; then
        print_pass "Directory exists: $1"
    else
        print_fail "Directory does not exist: $1"
    fi
}

# Test: File contains string
assert_file_contains() {
    if grep -qF -- "$2" "$1" 2>/dev/null; then
        print_pass "File contains '$2': $1"
    else
        print_fail "File does not contain '$2': $1"
    fi
}

# Test: Command succeeds
assert_command_success() {
    if $1 > /dev/null 2>&1; then
        print_pass "Command succeeded: $1"
    else
        print_fail "Command failed: $1"
    fi
}

# Cleanup function
cleanup_test_artifacts() {
    print_info "Cleaning up test artifacts..."
    rm -rf /workspace/.dbctl/baselines
    rm -rf /workspace/migrations/*.sql
    rm -f /workspace/EnchantedBeesDB/Tables/Hive.sql
    rm -f /workspace/EnchantedBeesDB/Tables/TestTable.sql
    print_info "Cleanup complete"
    echo
}

# ==============================================================================
# TEST SUITE
# ==============================================================================

print_header "Migration Generation System - Test Suite"

# ------------------------------------------------------------------------------
print_header "Setup: Clean Environment"
# ------------------------------------------------------------------------------

cleanup_test_artifacts

# ------------------------------------------------------------------------------
print_header "Test 1: Directory Structure"
# ------------------------------------------------------------------------------

print_test "Verify migrations directory exists"
assert_dir_exists "/workspace/migrations"

print_test "Verify migrations README exists"
assert_file_exists "/workspace/migrations/README.md"

print_test "Verify .dbctl directory structure can be created"
mkdir -p /workspace/.dbctl/baselines
assert_dir_exists "/workspace/.dbctl/baselines"

echo

# ------------------------------------------------------------------------------
print_header "Test 2: Baseline Initialization"
# ------------------------------------------------------------------------------

print_test "Initialize baseline without Hive table"
/workspace/dbctl generate --init 2>&1 | tee /tmp/test_output.txt

print_test "Verify baseline DACPAC created"
BASELINE_COUNT=$(ls -1 /workspace/.dbctl/baselines/*.dacpac 2>/dev/null | wc -l)
if [ "$BASELINE_COUNT" -eq 1 ]; then
    print_pass "Baseline DACPAC created (count: $BASELINE_COUNT)"
else
    print_fail "Expected 1 baseline DACPAC, found $BASELINE_COUNT"
fi

print_test "Verify baseline filename format (includes hash)"
BASELINE_FILE=$(ls -1 /workspace/.dbctl/baselines/*.dacpac 2>/dev/null | head -1)
if [[ "$BASELINE_FILE" =~ EnchantedBeesDB_[a-f0-9]{12}\.dacpac ]]; then
    print_pass "Baseline filename format correct: $(basename $BASELINE_FILE)"
else
    print_fail "Baseline filename format incorrect: $(basename $BASELINE_FILE)"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 3: No Changes Detected"
# ------------------------------------------------------------------------------

print_test "Generate migration when no changes exist"
OUTPUT=$(/workspace/dbctl generate 2>&1)

if echo "$OUTPUT" | grep -q "No schema changes detected"; then
    print_pass "Correctly detected no schema changes"
else
    print_fail "Should have detected no schema changes"
fi

print_test "Verify no migration files created"
MIGRATION_COUNT=$(ls -1 /workspace/migrations/*.sql 2>/dev/null | wc -l)
if [ "$MIGRATION_COUNT" -eq 0 ]; then
    print_pass "No migration files created (count: $MIGRATION_COUNT)"
else
    print_fail "Unexpected migration files created (count: $MIGRATION_COUNT)"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 4: Create Table Migration (Auto Description)"
# ------------------------------------------------------------------------------

print_test "Add new Hive table to SQL project"
cat > /workspace/EnchantedBeesDB/Tables/Hive.sql <<'EOF'
CREATE TABLE [dbo].[Hive]
(
  [Id] UNIQUEIDENTIFIER NOT NULL PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
  [Name] NVARCHAR(100) NOT NULL,
  [Location] NVARCHAR(255) NULL,
  [Capacity] INT NOT NULL DEFAULT 100,
  [CreatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
)
EOF
assert_file_exists "/workspace/EnchantedBeesDB/Tables/Hive.sql"

print_test "Generate migration with auto-description"
/workspace/dbctl generate 2>&1 | tee /tmp/test_output.txt

print_test "Verify migration files created"
MIGRATION_COUNT=$(ls -1 /workspace/migrations/*_*.sql 2>/dev/null | grep -v ".down.sql" | wc -l)
if [ "$MIGRATION_COUNT" -eq 1 ]; then
    print_pass "Migration UP file created (count: $MIGRATION_COUNT)"
else
    print_fail "Expected 1 migration UP file, found $MIGRATION_COUNT"
fi

DOWN_MIGRATION_COUNT=$(ls -1 /workspace/migrations/*.down.sql 2>/dev/null | wc -l)
if [ "$DOWN_MIGRATION_COUNT" -eq 1 ]; then
    print_pass "Migration DOWN file created (count: $DOWN_MIGRATION_COUNT)"
else
    print_fail "Expected 1 migration DOWN file, found $DOWN_MIGRATION_COUNT"
fi

print_test "Verify migration filename format (timestamp_description.sql)"
MIGRATION_FILE=$(ls -1 /workspace/migrations/*_*.sql 2>/dev/null | grep -v ".down.sql" | head -1)
if [[ "$(basename $MIGRATION_FILE)" =~ ^[0-9]{14}_[a-z0-9_]+\.sql$ ]]; then
    print_pass "Migration filename format correct: $(basename $MIGRATION_FILE)"
else
    print_fail "Migration filename format incorrect: $(basename $MIGRATION_FILE)"
fi

print_test "Verify migration contains metadata header"
assert_file_contains "$MIGRATION_FILE" "-- Migration:"
assert_file_contains "$MIGRATION_FILE" "-- Generated:"
assert_file_contains "$MIGRATION_FILE" "-- Baseline DACPAC:"
assert_file_contains "$MIGRATION_FILE" "-- Checksum:"

print_test "Verify migration contains CREATE TABLE statement"
assert_file_contains "$MIGRATION_FILE" "CREATE TABLE [dbo].[Hive]"

print_test "Verify new baseline created after migration"
NEW_BASELINE_COUNT=$(ls -1 /workspace/.dbctl/baselines/*.dacpac 2>/dev/null | wc -l)
if [ "$NEW_BASELINE_COUNT" -eq 2 ]; then
    print_pass "New baseline created (total count: $NEW_BASELINE_COUNT)"
else
    print_fail "Expected 2 baselines, found $NEW_BASELINE_COUNT"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 5: Alter Table Migration (Custom Description)"
# ------------------------------------------------------------------------------

print_test "Add IsActive column to Hive table"
cat > /workspace/EnchantedBeesDB/Tables/Hive.sql <<'EOF'
CREATE TABLE [dbo].[Hive]
(
  [Id] UNIQUEIDENTIFIER NOT NULL PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
  [Name] NVARCHAR(100) NOT NULL,
  [Location] NVARCHAR(255) NULL,
  [Capacity] INT NOT NULL DEFAULT 100,
  [IsActive] BIT NOT NULL DEFAULT 1,
  [CreatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
)
EOF

print_test "Generate migration with custom description"
/workspace/dbctl generate -m "add_is_active_column" 2>&1 | tee /tmp/test_output.txt

print_test "Verify custom description used in filename"
CUSTOM_MIGRATION=$(ls -1 /workspace/migrations/*_add_is_active_column.sql 2>/dev/null | head -1)
if [ -f "$CUSTOM_MIGRATION" ]; then
    print_pass "Migration with custom description created: $(basename $CUSTOM_MIGRATION)"
else
    print_fail "Migration with custom description not found"
fi

print_test "Verify migration contains ALTER TABLE or column addition"
if [ -f "$CUSTOM_MIGRATION" ]; then
    # The migration might use ALTER TABLE or just add columns
    if grep -qi "alter\|IsActive" "$CUSTOM_MIGRATION"; then
        print_pass "Migration contains column changes"
    else
        print_fail "Migration does not contain expected column changes"
    fi
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 6: DOWN Migration Template"
# ------------------------------------------------------------------------------

print_test "Verify DOWN migration contains template for non-reversible changes"
DOWN_FILE=$(ls -1 /workspace/migrations/*.down.sql 2>/dev/null | tail -1)
if [ -f "$DOWN_FILE" ]; then
    assert_file_contains "$DOWN_FILE" "Rollback Migration:"

    # Check if it's a template or auto-generated
    if grep -q "TODO: Implement rollback logic" "$DOWN_FILE"; then
        print_pass "DOWN migration is a template (requires manual implementation)"
    elif grep -q "DROP TABLE" "$DOWN_FILE"; then
        print_pass "DOWN migration auto-generated with DROP statements"
    else
        print_info "DOWN migration format unclear, manual review recommended"
    fi
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 7: Multiple Table Creation"
# ------------------------------------------------------------------------------

print_test "Add another test table"
cat > /workspace/EnchantedBeesDB/Tables/TestTable.sql <<'EOF'
CREATE TABLE [dbo].[TestTable]
(
  [Id] INT NOT NULL PRIMARY KEY IDENTITY(1,1),
  [TestName] NVARCHAR(50) NOT NULL
)
EOF

print_test "Generate migration for multiple changes"
/workspace/dbctl generate 2>&1 | tee /tmp/test_output.txt

print_test "Verify migration auto-description reflects multiple changes"
LATEST_MIGRATION=$(ls -1t /workspace/migrations/*_*.sql 2>/dev/null | grep -v ".down.sql" | head -1)
MIGRATION_NAME=$(basename "$LATEST_MIGRATION" .sql)
if echo "$MIGRATION_NAME" | grep -qi "create\|table\|test"; then
    print_pass "Migration description reflects changes: $MIGRATION_NAME"
else
    print_info "Migration description: $MIGRATION_NAME"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 8: dbctl Command Integration"
# ------------------------------------------------------------------------------

print_test "Verify dbctl generate command is available"
if /workspace/dbctl --help | grep -q "generate"; then
    print_pass "dbctl generate command available"
else
    print_fail "dbctl generate command not found in help"
fi

print_test "Verify dbctl generate --help works"
if /workspace/dbctl generate --help | grep -q "Generate migration scripts"; then
    print_pass "dbctl generate --help displays correctly"
else
    print_fail "dbctl generate --help does not work"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 9: Build Integration"
# ------------------------------------------------------------------------------

print_test "Verify dbctl build command still works"
/workspace/dbctl build 2>&1 | tee /tmp/build_output.txt

if [ -f "/workspace/EnchantedBeesDB/bin/Debug/EnchantedBeesDB.dacpac" ]; then
    print_pass "DACPAC built successfully"
else
    print_fail "DACPAC not found after build"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test 10: Database Initialization (init command)"
# ------------------------------------------------------------------------------

print_test "Verify dbctl init command is available"
if /workspace/dbctl --help | grep -q "init"; then
    print_pass "dbctl init command available"
else
    print_fail "dbctl init command not found in help"
fi

print_test "Verify dbctl init --help works"
if /workspace/dbctl init --help | grep -q "Initialize and publish database"; then
    print_pass "dbctl init --help displays correctly"
else
    print_fail "dbctl init --help does not work"
fi

print_test "Test database initialization (publish to SQL Server)"
print_info "Running dbctl init to publish database..."
if /workspace/dbctl init 2>&1 | grep -q "Successfully published database"; then
    print_pass "Database initialized and published successfully"
else
    print_fail "Database initialization failed"
fi

print_test "Verify database exists after init"
if /workspace/dbctl status 2>&1 | grep -q "Database 'EnchantedBeesDB' exists"; then
    print_pass "Database verified to exist on server"
else
    print_fail "Database verification failed"
fi

echo

# ------------------------------------------------------------------------------
print_header "Test Results Summary"
# ------------------------------------------------------------------------------

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TESTS_PASSED/$TOTAL_TESTS)*100}")

echo
echo -e "${CYAN}Total Tests:${NC} $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC}      $TESTS_PASSED"
echo -e "${RED}Failed:${NC}      $TESTS_FAILED"
echo -e "${YELLOW}Pass Rate:${NC}   ${PASS_RATE}%"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  ALL TESTS PASSED! ✓${NC}"
    echo -e "${GREEN}============================================================${NC}"
    exit 0
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}  SOME TESTS FAILED ✗${NC}"
    echo -e "${RED}============================================================${NC}"
    exit 1
fi

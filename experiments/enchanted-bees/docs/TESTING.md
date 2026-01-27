# Testing Guide

## Running the Test Suite

We maintain a comprehensive test suite to validate all migration generation functionality.

### Quick Start

From your host machine (outside the container):

```bash
./test.sh
```

Or from inside the dev container:

```bash
/workspace/test-migrations.sh
```

## Test Suite Coverage

The test suite validates database operations with **29 tests** covering:

### 1. Directory Structure (3 tests)
- ✅ Migrations directory exists
- ✅ Migrations README exists
- ✅ .dbctl directory structure

### 2. Baseline Initialization (3 tests)
- ✅ Baseline DACPAC creation
- ✅ Baseline filename format validation
- ✅ Baseline hash integrity

### 3. No Changes Detection (2 tests)
- ✅ Correctly detects when no schema changes exist
- ✅ No migration files created when unnecessary

### 4. Create Table Migration (6 tests)
- ✅ Migration files created (UP and DOWN)
- ✅ Filename format validation (timestamp_description.sql)
- ✅ Metadata header present (checksum, baseline reference, timestamp)
- ✅ SQL content validation (CREATE TABLE statements)
- ✅ New baseline created after migration

### 5. Alter Table Migration (2 tests)
- ✅ Custom description flag (`-m`) works
- ✅ ALTER statements generated correctly

### 6. DOWN Migration Templates (2 tests)
- ✅ Template generated for non-reversible changes
- ✅ Rollback metadata present

### 7. Multiple Changes (1 test)
- ✅ Auto-description reflects multiple table creations

### 8. CLI Integration (2 tests)
- ✅ `dbctl generate` command available
- ✅ Help documentation accessible

### 9. Build Integration (1 test)
- ✅ `dbctl build` continues to work

### 10. Database Initialization (4 tests)
- ✅ `dbctl init` command available
- ✅ Help documentation accessible
- ✅ Database successfully published to SQL Server
- ✅ Database verification after initialization

## Test Output

The test suite provides:
- ✅ **Color-coded results** (green=pass, red=fail)
- ✅ **Pass rate calculation**
- ✅ **Detailed test descriptions**
- ✅ **Clear failure messages**

### Example Output

```
============================================================
  Test Results Summary
============================================================

Total Tests: 29
Passed:      29
Failed:      0
Pass Rate:   100.0%

============================================================
  ALL TESTS PASSED! ✓
============================================================
```

## Continuous Testing

Run the test suite:
- ✅ After making changes to migration generation logic
- ✅ Before committing code
- ✅ As part of CI/CD pipeline (future)
- ✅ When debugging issues

## Test Artifacts

The test suite:
- Creates temporary test tables (Hive, TestTable)
- Generates test migrations
- Cleans up after itself (in Setup phase)
- Leaves test artifacts in place for inspection after completion

To manually clean up:

```bash
# Inside container
rm -rf /workspace/.dbctl/baselines
rm -rf /workspace/migrations/*.sql
rm -f /workspace/EnchantedBeesDB/Tables/Hive.sql
rm -f /workspace/EnchantedBeesDB/Tables/TestTable.sql
```

## Future Enhancements

As we build Epic 2, we'll add tests for:
- Migration execution
- Migration history tracking
- Rollback functionality
- Checksum validation
- Concurrent migration prevention

## Contributing Tests

When adding new features:
1. Add test cases to [test-migrations.sh](../test-migrations.sh)
2. Follow existing test patterns
3. Use helper functions (`assert_file_exists`, `assert_file_contains`, etc.)
4. Update this documentation
5. Ensure 100% pass rate before committing

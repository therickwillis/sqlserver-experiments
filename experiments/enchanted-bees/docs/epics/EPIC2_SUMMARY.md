# Epic 2: Migration Execution & Tracking - Summary

**Status**: ✅ Complete
**Completion Date**: 2026-01-28
**Test Coverage**: 47/47 tests passing (100%)

## Overview

Built a production-ready migration execution system that applies pending migrations to SQL Server, tracks applied migrations with checksums, validates integrity, and prevents concurrent execution conflicts.

## What We Built

### Core Features

1. **Migration Discovery & Validation**
   - Discovers all `.sql` files in `migrations/` directory
   - Sorts by timestamp for chronological execution
   - Validates checksums against `__MigrationsHistory` table
   - Detects tampering with previously applied migrations

2. **Migration Tracking**
   - `__MigrationsHistory` table tracks all applied migrations
   - Records: MigrationId, Checksum, AppliedAt, AppliedBy, ExecutionTimeMs, Success
   - SHA256 checksums for integrity validation
   - Execution time tracking for performance monitoring

3. **Concurrency Protection**
   - Uses SQL Server application locks (`sp_getapplock`)
   - Lock name: `DbMigrationLock`
   - Configurable timeout (default: 30 seconds)
   - Prevents multiple migrations running simultaneously

4. **Sqlcmd-Based Execution**
   - Executes migrations via `sqlcmd` subprocess
   - Preserves sqlpackage transaction management
   - Minimal SQL filtering (only SQLCMD-specific syntax)
   - 5-minute timeout per migration

5. **Dry-Run Support**
   - Preview pending migrations without applying
   - Shows what would be executed
   - No database changes made

6. **Status Reporting**
   - `dbctl status` shows applied/pending migrations
   - `dbctl migrate` shows execution progress
   - Execution time displayed for each migration

## Key Files Created

- `src/dbctl/migration_tracker.py` - Migration history management
- `src/dbctl/migration_executor.py` - Migration execution engine
- `src/dbctl/commands/migrate_command.py` - CLI migrate command
- Updated `src/dbctl/commands/status_command.py` - Migration status display
- Updated `test-migrations.sh` - Comprehensive test coverage (47 tests)

## Technical Implementation

### __MigrationsHistory Schema
```sql
CREATE TABLE [dbo].[__MigrationsHistory] (
    MigrationId NVARCHAR(255) NOT NULL PRIMARY KEY,
    Checksum NVARCHAR(64) NOT NULL,
    AppliedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    AppliedBy NVARCHAR(100) NOT NULL,
    ExecutionTimeMs INT NOT NULL,
    Success BIT NOT NULL
);
```

### Sqlcmd Execution
```python
result = subprocess.run(
    [
        'sqlcmd',
        '-S', server,
        '-U', user,
        '-P', password,
        '-d', database,
        '-b',  # Abort batch on error
        '-C',  # Trust server certificate
    ],
    input=cleaned_sql,
    capture_output=True,
    text=True,
    timeout=300
)
```

### SQLCMD Syntax Filtering
```python
# Remove SQLCMD variable definitions
content = re.sub(r'^:setvar\s+.*$', '', content, flags=re.MULTILINE)

# Remove SQLCMD mode check block
sqlcmd_check_pattern = r"IF\s+N'\$\(__IsSqlCmdEnabled\)'\s+NOT\s+LIKE\s+N'True'\s+BEGIN.*?END"
content = re.sub(sqlcmd_check_pattern, '', content, flags=re.DOTALL)
```

## Challenges Overcome

### 1. Transaction Management Conflicts

**Initial Approach (Failed)**:
- Used pyodbc to execute migrations with `cursor.execute()`
- Created nested transactions (pyodbc + sqlpackage)
- Migrations appeared to succeed but didn't persist

**Solution**:
- Execute migrations via `sqlcmd` subprocess
- Let sqlpackage scripts manage their own transactions
- pyodbc connection only for tracking and queries
- Use `autocommit=True` for pyodbc connection

### 2. SQLCMD Syntax Compatibility

**Issue**: sqlpackage generates scripts with SQLCMD-specific syntax
- `:setvar` variable definitions
- `:on error exit` directives
- `IF N'$(__IsSqlCmdEnabled)'` mode checks
- `USE [$(DatabaseName)]` database switching

**Solution**: Regex-based filtering to remove SQLCMD commands while preserving SQL

### 3. FreeTDS Driver Limitations

**Issue**: MacOS uses FreeTDS instead of "ODBC Driver 18 for SQL Server"

**Solution**:
- Updated connection string to use FreeTDS driver
- Removed unsupported TDS features
- Tested on Azure SQL Edge (SQL 2019 engine)

### 4. Unnamed Constraints

**Issue**: Sqlpackage generates invalid SQL for unnamed default constraints
- `ALTER TABLE [dbo].[Hive] DROP CONSTRAINT ;` (missing name)

**Solution**:
- Use explicitly named constraints in SQL project
- `CONSTRAINT DF_TableName_ColumnName DEFAULT value`
- Updated test fixtures to use named constraints

## Architecture Decisions

### Why Sqlcmd Instead of Pyodbc?

**Sqlcmd Advantages**:
- ✅ Handles sqlpackage transaction management correctly
- ✅ Preserves migration files as-is (single source of truth)
- ✅ Simpler error handling
- ✅ Native SQL Server tool

**Pyodbc Disadvantages**:
- ❌ Creates nested transactions
- ❌ Requires complex SQL manipulation
- ❌ Driver-specific issues (FreeTDS)

### Why SHA256 Checksums?

- **Integrity validation**: Detect tampering with applied migrations
- **Security**: Cryptographically secure hash
- **Standard**: Widely supported, Git uses SHA256
- **File-based**: No database dependency for checksum calculation

### Why Application Locks?

**Alternatives Considered**:
- File-based locks: Not suitable for distributed systems
- Optimistic locking: Race conditions possible
- Advisory locks: Not portable across databases

**sp_getapplock Benefits**:
- ✅ Built into SQL Server
- ✅ Automatic cleanup on connection close
- ✅ Configurable timeout
- ✅ Works across distributed systems

## Test Coverage

**47 tests** (18 new for Epic 2) covering:

### Epic 1 Tests (Existing)
- Directory structure and baseline
- Migration generation workflow
- CLI integration

### Epic 2 Tests (New)
- ✅ Dry-run functionality
- ✅ Migration application
- ✅ __MigrationsHistory tracking
- ✅ Database schema verification
- ✅ Status reporting
- ✅ Idempotency (no duplicate migrations)
- ✅ Sequential migration execution
- ✅ New migrations after initial apply
- ✅ Checksum recording
- ✅ Execution time tracking

## Usage Examples

### Apply Pending Migrations
```bash
dbctl migrate
# ============================================================
#   Database Migration
# ============================================================
#
# Step 1: Connecting to database...
# ✓ Connected successfully
#
# Step 2: Initializing migration tracking...
# ✓ Migration history table ready
#
# Step 3: Discovering migrations...
#   Total migrations: 3
#   Applied: 1
#   Pending: 2
#
# Step 4: Validating migration integrity...
# ✓ All migrations validated
#
# Step 5: Pending migrations:
#   • 20260127151608_add_lastused_tracking
#     Add Lastused Tracking
#   • 20260127151849_add_api_authentication
#     Add Api Authentication
#
# Step 6: Applying migrations...
#   ✓ 20260127151608_add_lastused_tracking
#     Executed in 43ms
#   ✓ 20260127151849_add_api_authentication
#     Executed in 38ms
#
# ============================================================
#   Migration Complete!
# ============================================================
#
# Successfully applied 2 migration(s).
# Database is now up to date!
```

### Dry-Run Preview
```bash
dbctl migrate --dry-run
# Shows pending migrations without applying
```

### Check Status
```bash
dbctl status
# Database Status
#
# Connection:
#   Server: sqlserver:1433
#   Database: EnchantedBeesDB
#   User: sa
#
# ✓ Database server is reachable
# ✓ Database 'EnchantedBeesDB' exists
#
# Migrations:
#   Total migrations: 3
#   Applied: 3
#   Pending: 0
#   ✓ Database is up to date!
```

## Integration with Existing Tools

- **VS Code Tasks**: Added "dbctl: Migrate" task
- **Docker Compose**: Runs inside dev container
- **Test Suite**: Integrated into `test-migrations.sh`
- **Status Command**: Shows migration state

## Error Handling

### Migration Failure Behavior
1. **Stop on First Failure**: Don't apply subsequent migrations
2. **Rollback**: sqlpackage scripts handle rollback
3. **Clear Error Messages**: Show SQL error with line numbers
4. **Status Tracking**: Failed migrations not recorded

### Lock Acquisition Failure
- **Timeout**: Default 30 seconds
- **Error Message**: "Could not acquire migration lock after N seconds"
- **Resolution**: Wait for concurrent migration to complete

### Checksum Mismatch
- **Detection**: Compare file checksum with recorded checksum
- **Error Message**: "Migration X has been modified since it was applied"
- **Resolution**: Investigate changes, never modify applied migrations

## What's Next

Epic 2 enables:
- ✅ Production deployment workflow
- 🔜 Epic 3: Rollback support (execute `.down.sql` files)
- 🔜 Epic 4: CI/CD integration
- 🔜 Multi-environment support (dev/staging/prod)

## Metrics

- **Lines of Code**: ~600 Python (Epic 2 additions)
- **Test Coverage**: 47 tests (100% pass rate)
- **Execution Method**: Sqlcmd subprocess
- **Average Migration Time**: 40-80ms per migration
- **Lock Timeout**: 30 seconds (configurable)

## Key Learnings

1. **Respect Tool Boundaries**: Let sqlpackage manage transactions, don't interfere
2. **Subprocess Over Library**: Sometimes simpler to shell out than fight library limitations
3. **Minimal Manipulation**: Filter only what's necessary (SQLCMD syntax), preserve migration logic
4. **Named Constraints**: Always use explicit constraint names in SQL Server projects
5. **Test Everything**: Comprehensive tests caught transaction persistence issues early

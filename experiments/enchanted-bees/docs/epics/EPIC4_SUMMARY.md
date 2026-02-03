# Epic 4: Environment Drift Detection - Summary

**Status**: Incomplete - Needs Revisiting
**Started**: 2026-01-30
**Test Coverage**: 8/18 drift tests passing (44%)

## Overview

Added environment drift detection that compares live database state against the expected SQL project state using DACPAC comparison. The system extracts a DACPAC from the live database, compares it against the project DACPAC, categorizes differences by tolerance level, and reports results in multiple formats. Includes integration with `dbctl migrate` to gate deployments on drift status.

## What We Built

### Core Features

1. **Drift Detection Pipeline**
   - Builds project DACPAC (expected state) via `dotnet build`
   - Extracts live database DACPAC (actual state) via `sqlpackage /Action:Extract`
   - Compares schemas via `sqlpackage /Action:DeployReport`
   - Categorizes changes by drift type: MISSING_OBJECT, EXTRA_OBJECT, MODIFIED_OBJECT, ACCEPTABLE
   - Temporary file cleanup after comparison

2. **Tolerance Levels**
   - `STRICT`: Any difference is drift
   - `NORMAL` (default): Allows auto-generated statistics and performance indexes (`_WA_Sys_` prefix, `IX_`/`IDX_`/`Performance`/`Perf` prefixes for CREATEs)
   - `PERMISSIVE`: Also allows extended properties and descriptions

3. **Output Formats**
   - Table (default): Human-readable with drift categorization
   - JSON: Structured data for tooling integration
   - XML: Raw sqlpackage report

4. **Repair Migration Generation**
   - `--fix` flag generates repair migration from drift detection SQL script
   - DROP statements auto-commented for safety (requires manual review)
   - Paired `.sql` and `.down.sql` files with template warnings

5. **CI/CD Integration**
   - `--exit-code` flag: Returns 0 (no drift), 1 (drift detected), 2 (error)
   - `--report-file` flag: Saves detailed reports to disk
   - `--dry-run` flag: Preview without connecting

6. **Migration Gating**
   - `dbctl migrate --validate-drift` blocks migration if unacceptable drift detected
   - `--force` flag overrides drift check with warnings

### CLI Flags

```
dbctl drift [options]

  --output      table | json | xml (default: table)
  --tolerance   strict | normal | permissive (default: normal)
  --fix         Generate repair migration to fix drift
  --exit-code   Return non-zero exit code on drift
  --baseline    Compare against specific DACPAC file
  --dry-run     Preview without connecting to database
  --report-file Save detailed report to file
```

## Key Files Created

- `src/dbctl/drift_detector.py` - Core drift detection module (~527 lines)
  - `extract_database_dacpac()` - Extracts schema from live database
  - `compare_database_to_project()` - Compares expected vs actual state
  - `categorize_drift()` - Classifies changes by tolerance level
  - `generate_drift_report()` - Formats output as table/JSON/XML
  - `generate_repair_migration()` - Auto-generates repair migrations
  - `is_acceptable_drift()` - Determines if drift is acceptable
- `src/dbctl/commands/drift_command.py` - CLI command implementation (~372 lines)
- `test-drift.sh` - Test suite (~403 lines, 18 tests)

## Key Files Modified

- `src/dbctl/cli.py` - Registered `drift` command
- `src/dbctl/commands/migrate_command.py` - Added `--validate-drift` and `--force` flags
- `src/dbctl/migration_executor.py` - Refactored from subprocess sqlcmd to direct pyodbc execution
- `src/dbctl/rollback_executor.py` - Updated to use pyodbc (consistency with executor change)

## Technical Implementation

### DACPAC Extraction from Live Database

```python
sqlpackage /Action:Extract \
    /SourceConnectionString:"Server=sqlserver;Database=EnchantedBeesDB;User Id=sa;Password=...;TrustServerCertificate=True" \
    /TargetFile:"/tmp/live_database.dacpac"
```

Uses `/SourceConnectionString` instead of individual server/database parameters to support `TrustServerCertificate=True` for self-signed certs.

### Schema Comparison

```python
sqlpackage /Action:DeployReport \
    /SourceFile:"project.dacpac" \
    /TargetFile:"live_database.dacpac" \
    /OutputPath:"/tmp/drift_report.xml"
```

### Execution Strategy Change (Post-Epic 4 Fix)

Migrated from subprocess-based `sqlcmd` to direct `pyodbc` execution to fix Mac compatibility:

```python
# Before (subprocess):
subprocess.run(['sqlcmd', '-S', server, ...], input=sql)

# After (pyodbc):
def _execute_sql_via_pyodbc(sql, server, database, user, password):
    conn = pyodbc.connect(conn_str, autocommit=True)
    for batch in _split_sql_batches(sql):
        cursor.execute(batch)
```

Applies to migrations, rollbacks, and drift repairs. Splits SQL on `GO` separators to maintain batch semantics.

## Architecture Decisions

### Why DACPAC-to-DACPAC Comparison?

**Chosen Approach**: Extract live DB to DACPAC, then compare two DACPACs

**Benefits**:
- Reuses proven sqlpackage tooling from Epic 1
- Consistent comparison regardless of environment
- XML output is structured and parseable
- sqlpackage handles all SQL Server object types

### Why Three Tolerance Levels?

**Problem**: Not all schema differences are meaningful drift. SQL Server auto-creates statistics and performance indexes that shouldn't block deployments.

**Solution**: Configurable tolerance lets teams choose their strictness:
- CI/CD pipelines can use `strict` for production
- Development environments can use `permissive`
- Default `normal` covers the common case

### Why Comment Out DROP Statements in Repairs?

**Risk**: Auto-generated repair migrations can include DROP TABLE/COLUMN statements that destroy data.

**Solution**: DROP operations are auto-commented, forcing manual review. This follows Epic 3's safety-first pattern.

## Issues to Revisit

### Test Results (8 passed, 10 failed)

#### Working

| Test | Group |
|------|-------|
| No drift on clean database | Basic Detection |
| Exit code 0 when no drift | Basic Detection |
| Detect drift when extra table exists | Basic Detection |
| Strict tolerance detects all drift | Tolerance Levels |
| Save drift report to file | Report Saving |
| Dry-run mode works | Dry-Run |
| Migrate validates no drift | Migrate Integration |
| Drift detection with baseline DACPAC | Migrate Integration |

#### Broken

**1. `--exit-code` flag not returning correct exit codes**
- When drift exists, `--exit-code` returns 0 instead of expected 1
- Impact: CI/CD pipelines cannot gate on drift status
- Root cause: Exit code logic not wired to drift detection result

**2. JSON output format incomplete**
- Missing `has_drift` field in JSON output
- Missing `drift_count` field in JSON output
- Impact: Tooling integration broken for structured consumers

**3. XML output format failing**
- XML report generation fails entirely
- Impact: Raw sqlpackage report not accessible via CLI

**4. Normal tolerance mode fails**
- Default tolerance level (`normal`) errors out
- Impact: The most common usage path is broken
- Note: `strict` mode works, suggesting issue is in the acceptable drift filtering logic

**5. Repair migration generation not working**
- `--fix` flag does not create repair migration files
- Safety warning and DOWN file checks skipped (no file produced)
- Impact: Cannot auto-generate fixes for detected drift

**6. Migration drift gating not blocking**
- `dbctl migrate --validate-drift` does not block when drift is detected
- `--force` override path untestable because blocking itself doesn't work
- Impact: Deployment safety gate is non-functional

### Additional Concerns

**7. Constraint collision on rollback + re-apply**
- Test output shows: `There is already an object named 'DF_Hive_IsActive' in the database`
- Occurs when rolling back and re-applying migrations with named constraints
- Not drift-specific, but affects the repair migration workflow

**8. CI/CD exit codes untested in a real pipeline**
- Exit code scheme (0/1/2) is implemented but only tested locally
- Pipeline integration not validated end-to-end

**9. Template DOWN migrations are placeholders**
- Repair migrations produce `.down.sql` files with TODO markers
- Rollback executor blocks these correctly, but any repair migration requires manual completion

## What Works vs What Doesn't

| Capability | Status | Notes |
|------------|--------|-------|
| Core drift detection | Working | Detects extra tables in database |
| DACPAC extraction | Working | sqlpackage Extract succeeds |
| Schema comparison | Working | sqlpackage DeployReport succeeds |
| Strict tolerance | Working | All differences flagged as drift |
| Normal tolerance | Broken | Acceptable drift filtering fails |
| Table output | Working | Default format renders |
| JSON output | Broken | Missing required fields |
| XML output | Broken | Format generation fails |
| `--exit-code` flag | Broken | Always returns 0 |
| `--fix` flag | Broken | No repair file generated |
| `--dry-run` flag | Working | Preview mode functional |
| `--baseline` flag | Working | Custom DACPAC comparison works |
| `--report-file` flag | Working | Report saves to disk |
| `--validate-drift` | Broken | Does not block migrations |
| `--force` override | Broken | Untestable (gating broken) |
| pyodbc execution | Working | Mac compatibility fix applied |

## Test Coverage

**18 tests total** (8 passing, 10 failing):

- Basic Drift Detection: 3/6 passing
- Drift Tolerance Levels: 1/2 passing
- Repair Migration Generation: 0/3 passing
- Drift Report Saving: 1/1 passing
- Dry-Run Mode: 1/1 passing
- Migrate Integration: 2/5 passing

## Metrics

- **Lines of Code**: ~899 Python (drift_detector.py + drift_command.py)
- **Test Suite**: 403 lines, 18 tests
- **Pass Rate**: 44% (needs work)
- **Tolerance Levels**: 3 (strict, normal, permissive)
- **Output Formats**: 3 (table, JSON, XML)
- **CLI Flags**: 7 new flags on `dbctl drift`

## Key Learnings

1. **Core detection works, plumbing doesn't**: The sqlpackage-based comparison pipeline is solid. The failures are in output formatting, exit code wiring, and integration hooks — not in the detection itself.

2. **Default path must work first**: Normal tolerance is the default and it's broken. Strict works because it skips the filtering logic. The acceptable drift categorization needs debugging.

3. **pyodbc migration was necessary**: Switching from subprocess sqlcmd to direct pyodbc fixed Mac execution but changed the execution model across the entire codebase (migrations, rollbacks, repairs).

4. **Safety patterns carry forward**: The commented-out DROP statements and template DOWN files from Epic 3's patterns are correctly applied here, even though the generation path itself needs fixing.

## What's Next

Before Epic 4 can be marked complete, the following must be addressed:

1. Fix `--exit-code` to return 1 when drift is detected
2. Fix JSON output to include `has_drift` and `drift_count` fields
3. Fix XML output format generation
4. Debug normal tolerance mode (acceptable drift filtering)
5. Fix `--fix` flag to generate repair migration files
6. Fix `--validate-drift` to block migrations when drift exists
7. Verify `--force` override works once gating is fixed
8. Get test suite to 18/18 passing

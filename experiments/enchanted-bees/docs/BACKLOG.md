# MSSQL Database Management - Product Backlog

## Project Vision

Develop a turn-key solution for managing MSSQL databases from development to production, focusing on developer experience and artifact-based deployments using migration scripts.

## Guiding Principles

1. **Container-First:** All tooling and services run in containers for consistency across Windows/Mac/Linux and between local development and CI/CD pipelines
2. **Environment Parity:** Eliminate schema drift by ensuring all environments are managed through the same artifact-based deployment process
3. **Developer Experience:** Simple, intuitive workflows that build confidence in database changes
4. **Testing & Quality:** Comprehensive testing framework to validate schema, data integrity, and migration safety
5. **Universal Applicability:** While EnchantedBees is our test case, the solution should work for any MSSQL database

## Key Technical Decisions

- **Deployment Artifacts:** Timestamp-based migration scripts stored in version control
- **Schema Source of Truth:** SQL Project (.sqlproj) with baseline DACPAC generation for comparison
- **Target Environments:** Dev, Staging, Production, plus ephemeral PR/feature environments
- **Container Strategy:** Use official Microsoft SQL Server and tooling images
- **CLI Design:** Single CLI tool usable by both developers and CI pipelines
- **VS Code Integration:** Favor flawless, simple solutions (devcontainer, tasks, or remote-containers)
- **Implementation Language:** Python (to keep the project simple with fewer languages)

---

## Epic 0: Container Infrastructure (Foundation)

**Goal:** Establish container-based tooling that works identically on all platforms and in CI pipelines

**Priority:** Must complete before other epics can progress

### User Stories

- [x] As a developer on any OS, I can run all database operations through containers
- [x] As a developer, I have a container image with all SQL tooling (sqlpackage, migration tools, etc.)
- [x] As a developer, I can use docker-compose to orchestrate SQL Server + tooling containers
- [x] As a developer, my VS Code connects to and works with containerized services
- [x] As a CI pipeline, I use the same container images as local development
- [x] As a developer, I can mount my workspace into containers to see live changes
- [x] As a developer, container images are versioned and immutable for reproducibility

**Status:** ✅ Complete (2026-01-27)

**Deliverables:**
- Updated [dev.Dockerfile](dev.Dockerfile) with sqlpackage pre-installed
- Python CLI tool `dbctl` with commands: `info`, `build`, `status`
- VS Code [tasks.json](.vscode/tasks.json) for common operations
- [GETTING_STARTED.md](GETTING_STARTED.md) documentation
- Devcontainer configuration for seamless VS Code integration

---

## Epic 1: Migration Generation System

**Goal:** Enable developers to generate timestamp-based migration scripts from SQL project changes

**Priority:** High (First major capability)

**Status:** ✅ Complete (2026-01-27)

### User Stories

- [x] As a developer, I can run a containerized command to build my SQL project and generate a DACPAC
- [x] As a developer, I can run a containerized tool to compare DACPACs and detect schema changes
- [x] As a developer, I can auto-generate a timestamp-based migration script (UP) from detected changes
- [x] As a developer, I can generate rollback migrations (DOWN) when possible
- [x] As a developer, I can handle complex migrations (renames, data transformations) with templated scripts
- [x] As a developer, I can see a migration preview before generating files
- [x] As a developer, I can track which baseline DACPAC was used for each migration
- [x] As a developer, migration generation works identically on Windows, Mac, and Linux via containers

### Technical Notes

- Use `sqlpackage` for DACPAC builds and schema comparisons
- Timestamp format: `YYYYMMDDHHMMSS_description.sql` (e.g., `20260127143022_add_bee_species_table.sql`)
- Store baseline DACPAC reference in migration metadata
- Consider edge cases: column renames vs add/drop, table renames, etc.

### Deliverables

- ✅ `dbctl generate` command with auto-description and custom `-m` flag
- ✅ Baseline DACPAC management in `.dbctl/baselines/`
- ✅ Migration files with metadata headers (checksum, baseline reference, timestamp)
- ✅ AUTO-generated DOWN migrations for reversible changes
- ✅ Template DOWN migrations for complex changes requiring manual review
- ✅ VS Code tasks for migration generation
- ✅ Comprehensive test suite: [test-migrations.sh](../test-migrations.sh) (25 tests, 100% pass rate)

---

## Epic 2: Migration Execution & Tracking

**Goal:** Apply migrations reliably and track state across environments

**Priority:** High (Required for basic workflow)

**Status:** ✅ Complete (2026-01-28)

### User Stories

- [x] As a developer, I can apply pending migrations using containerized tooling
- [x] As a system, I track which migrations have been applied (migrations history table)
- [x] As a developer, I can see the migration status of any environment through containerized CLI
- [x] As a developer, I can validate migrations before applying them (dry-run)
- [ ] ~~As a developer, I can rollback the last migration if needed~~ → Moved to Epic 3
- [x] As a developer, I can run migrations in a transaction (when safe)
- [x] As a CI pipeline, I run the exact same migration container as local development

### Technical Notes

- Create `__MigrationsHistory` table to track applied migrations (timestamp, checksum, applied_at, etc.)
- Support both transactional and non-transactional migrations
- Validate migration checksums to detect tampering
- Lock mechanism to prevent concurrent migrations

### Deliverables

- ✅ `dbctl migrate` command with dry-run support
- ✅ `__MigrationsHistory` table tracking (MigrationId, Checksum, AppliedAt, AppliedBy, ExecutionTimeMs, Success)
- ✅ SHA256 checksum validation on all migrations
- ✅ Application lock (`sp_getapplock`) for concurrency protection
- ✅ Sqlcmd-based execution preserving sqlpackage transaction management
- ✅ Updated `dbctl status` with migration state display
- ✅ Comprehensive test suite: 47/47 tests (100% pass rate)

### Key Learnings

- **Sqlcmd over pyodbc**: Shell out to sqlcmd rather than fighting nested transaction issues
- **Minimal SQL filtering**: Only remove SQLCMD-specific syntax (`:setvar`, `:on error exit`), preserve migration logic
- **Named constraints required**: Always use explicit constraint names in SQL projects to avoid sqlpackage bugs
- **Respect tool boundaries**: Let sqlpackage manage transactions, don't interfere

---

## Epic 3: Rollback & Testing Framework

**Goal:** Enable safe rollbacks and build confidence in database changes through automated testing

**Priority:** High (Quality gate for deployments)

**Status:** 🔄 Partially Complete (Rollback: ✅ Complete, Testing Framework: 📋 Backlog)

### User Stories

**Rollback Support** (deferred from Epic 2):
- [x] As a developer, I can rollback the last N migrations using `.down.sql` files
- [x] As a developer, I can see rollback status in `dbctl status`
- [x] As a developer, rollbacks update `__MigrationsHistory` appropriately
- [x] As a developer, I can preview a rollback with `--dry-run`

**Testing Framework** (deferred to future):
- [ ] As a developer, I can run all tests in an isolated container environment
- [ ] As a developer, I can define schema validation tests (tables, columns, constraints exist)
- [ ] As a developer, I can define data integrity tests (constraints are enforced)
- [ ] As a developer, I can test that migrations run successfully against test data
- [ ] As a developer, I can test migration rollbacks don't lose data
- [ ] As a developer, I can run all tests with a single containerized command (`dbctl test`)
- [ ] As a developer, I can see clear test results and failures
- [ ] As a CI pipeline, I run the same test container image as local development

### Technical Notes

**Rollback Implementation**:
- Use existing `.down.sql` files generated by Epic 1
- Reuse sqlcmd execution pattern from Epic 2 (don't use pyodbc for execution)
- Track rollback in `__MigrationsHistory` (either mark as rolled back or delete row)
- Validate DOWN migration exists before allowing rollback
- Consider: should rollback require explicit confirmation?

**Testing Implementation**:
- Leverage existing bash test patterns from `test-migrations.sh` (47 tests, 100% pass)
- Consider pytest for more structured test organization
- Test types:
  - Schema tests: Assert table/column/constraint existence
  - Data integrity tests: Attempt to violate constraints, ensure failure
  - Migration tests: Apply migrations to test DB, validate success
  - Rollback tests: Apply then rollback, ensure no data loss
- Support test fixtures and seed data for testing
- Named constraints are required (learning from Epic 2)

### Deliverables (Rollback Support - Complete)

- ✅ `dbctl rollback` command with `--force` and `--dry-run` support
- ✅ `RolledBackAt` and `RolledBackBy` columns in `__MigrationsHistory`
- ✅ Backwards compatibility with `ensure_rollback_columns()` auto-upgrade
- ✅ Multi-migration rollback with `--count N` parameter
- ✅ Template `.down.sql` detection (blocks rollback if TODO marker present)
- ✅ Missing `.down.sql` file detection and validation
- ✅ Updated `dbctl status` with rollback information display
- ✅ Comprehensive test suite: 65/65 tests (100% pass rate)
- ✅ Complete audit trail (migrations marked as rolled back, not deleted)
- ✅ Safety features (force flag required, dry-run preview, eligibility validation)

---

## Epic 4: Environment Drift Detection

**Goal:** Prevent and detect schema drift across environments

**Priority:** Medium (Key pain point to solve)

**Status:** ✅ Complete (2026-01-31)

### User Stories

- [x] As a developer, I can compare two database environments using `dbctl drift`
- [x] As a developer, I can detect drift between my local DB and the migration scripts
- [x] As a developer, I can see a report of schema differences between environments
- [x] As a system, I can block deployments if target environment has unexpected drift
- [x] As a developer, I can generate a "repair" migration to fix drift
- [x] As a CI pipeline, I can run drift detection as part of deployment validation

### Technical Notes

**Leveraging Existing Patterns**:
- Reuse DACPAC comparison via `sqlpackage /Action:DeployReport` (Epic 1 pattern)
- Reuse XML parsing patterns from `dacpac_utils.py`
- If repair scripts needed, use sqlcmd execution pattern (Epic 2 pattern)
- Follow minimal SQL manipulation principle

**Implementation Approach**:
- Compare target environment against:
  1. Expected state from migrations (build DACPAC from SQL project)
  2. Current state (extract DACPAC from live database)
- Configurable drift tolerance (some drift may be acceptable in certain scenarios)
- Generate repair scripts automatically when possible
- Integration with `dbctl migrate --validate-drift` to check drift before applying

### Deliverables

- ✅ `drift_detector.py` - Core drift detection module
  - `extract_database_dacpac()` - Extract schema from live database using sqlpackage
  - `compare_database_to_project()` - Compare expected vs actual state
  - `categorize_drift()` - Classify drift by tolerance level (strict, normal, permissive)
  - `generate_drift_report()` - Format output as table, JSON, or XML
  - `generate_repair_migration()` - Auto-generate repair migrations with safety warnings
- ✅ `drift_command.py` - CLI command implementation with full feature set
  - `--output` flag for table/JSON/XML formats
  - `--tolerance` flag for strict/normal/permissive drift categorization
  - `--fix` flag to generate repair migrations
  - `--exit-code` flag for CI/CD integration
  - `--baseline` flag to compare against specific baseline DACPAC
  - `--dry-run` flag to preview without connecting
  - `--report-file` flag to save detailed reports
- ✅ Integration with `dbctl migrate --validate-drift` command
  - Blocks migrations when unacceptable drift detected
  - `--force` flag to override drift check
  - Clear error messages with drift remediation suggestions
- ✅ Comprehensive test suite: [test-drift.sh](../test-drift.sh) (17 tests)
  - Basic drift detection tests
  - Tolerance level tests
  - Repair migration generation tests
  - Report saving and output format tests
  - Dry-run mode tests
  - Migrate integration tests
- ✅ Safety features:
  - DROP statements commented out in repair migrations (manual review required)
  - Template DOWN migrations for complex rollbacks
  - Acceptable drift patterns (performance indexes, statistics)
  - Exit codes for scripting (0=no drift, 1=drift detected, 2=error)

### Key Technical Decisions

- **sqlpackage Extract**: Used `/SourceConnectionString` with `TrustServerCertificate=True` for self-signed cert support
- **Tolerance Levels**: Three levels implemented - strict (any change is drift), normal (allows perf indexes/stats), permissive (also allows extended properties)
- **Safety-First Repairs**: DROP operations commented out by default, requiring manual review before execution
- **CI/CD Ready**: `--exit-code` flag returns non-zero when drift detected, perfect for pipeline integration
- **Reused Patterns**: Leveraged Epic 1's DACPAC comparison, Epic 2's sqlcmd execution, Epic 3's safety patterns

---

## Epic 5: Developer Experience & Onboarding

**Goal:** Make it simple to get started and work efficiently on any platform

**Priority:** Medium (Reduces friction, increases adoption)

### User Stories

**Already Complete** (from Epics 0-2):
- [x] As a new developer on any OS, I can run `docker compose up` and have a working environment
- [x] As a developer, I have a VS Code devcontainer configuration that provides consistent tooling
- [x] As a developer, I can use VS Code commands/tasks that execute in containers
- [x] As a developer, I don't need to install SQL Server tools locally - containers provide everything
- [x] As a Mac developer with ARM, containers work natively (Azure SQL Edge)

**Remaining Work**:
- [ ] As a developer, I have clear CLI commands for all operations (init, migrate, test, drift, rollback)
- [ ] As a developer, I can see helpful error messages when things go wrong (audit & improve)
- [ ] As a developer, I have documentation and examples for common scenarios
- [ ] As a Windows developer, everything works without WSL complexity (needs testing)
- [ ] As a developer, I have a quick-start guide that gets me productive in < 15 minutes
- [ ] As a developer, CLI help text is comprehensive and useful

### Technical Notes

**Current CLI Commands** (implemented):
- ✅ `dbctl info` - Environment information
- ✅ `dbctl build` - Build SQL project to DACPAC
- ✅ `dbctl status` - Show migration status
- ✅ `dbctl generate` - Generate migration from schema changes
- ✅ `dbctl migrate` - Apply pending migrations
- ⏳ `dbctl init` - Initialize new database project (placeholder exists)

**Commands to Add** (from other epics):
- `dbctl rollback` - Rollback migrations (Epic 3)
- `dbctl test` - Run test suite (Epic 3)
- `dbctl drift` - Detect schema drift (Epic 4)

**Documentation Gaps**:
- Troubleshooting guide for common issues
- Windows-specific setup instructions
- Migration workflow examples (feature branch, hotfix, etc.)
- Team workflow documentation (multiple developers)

---

## Epic 6: CI/CD & Ephemeral Environments

**Goal:** Support automated deployments and PR-based environments

**Priority:** Medium (Enables full workflow)

### User Stories

- [ ] As a CI pipeline, I can pull the same versioned container images used in development
- [ ] As a CI pipeline, I can build and validate database artifacts in containers
- [ ] As a CI pipeline, I can create ephemeral databases for PR environments using containers
- [ ] As a CI pipeline, I can run tests against ephemeral environments
- [ ] As a CI pipeline, I can deploy migrations to staging/production using containers
- [ ] As a CI pipeline, I can tear down ephemeral environments after PR close
- [ ] As a DevOps engineer, I can configure deployment strategies (auto vs manual approval)
- [ ] As a CI pipeline, I never have "works locally but fails in CI" issues due to environment differences

### Technical Notes

**Leveraging Existing Patterns**:
- Reuse Docker Compose patterns for ephemeral databases
- Reuse test-migrations.sh patterns for CI validation
- Container-first approach ensures local/CI parity
- Use same sqlcmd execution pattern for deployments

**Implementation Approach**:
- Start with GitHub Actions (most common)
- Ephemeral environment naming: `db-pr-{PR_NUMBER}` or similar
- Consider Azure SQL, AWS RDS, and containerized SQL Server for ephemeral environments
- Deployment safety checks:
  - Run tests before deployment (Epic 3)
  - Check for drift (Epic 4)
  - Validate migration checksums (already implemented)
  - Optional manual approval gate

**CI Workflow Stages**:
1. Build: `dbctl build` - compile SQL project
2. Generate: `dbctl generate --check` - verify no uncommitted schema changes
3. Test: `dbctl test` - run test suite against ephemeral DB
4. Drift: `dbctl drift` - validate target environment
5. Deploy: `dbctl migrate` - apply pending migrations

---

## Roadmap Phases

### Phase 1: Foundation ✅ COMPLETE
**Goal:** Basic migration generation and execution

- ✅ Epic 0: Container Infrastructure (Complete - 2026-01-27)
- ✅ Epic 1: Migration Generation System (Complete - 2026-01-27)
- ✅ Epic 2: Migration Execution & Tracking (Complete - 2026-01-28)

**Success Criteria:** ✅ All met
- ✅ Developer can generate migrations from SQL project changes
- ✅ Developer can apply migrations to local database
- ✅ All operations run in containers
- ✅ 47/47 tests passing (100% coverage)

### Phase 2: Quality & Confidence ✅ COMPLETE
**Goal:** Build trust through testing, rollback, and drift detection

- ✅ Epic 3: Rollback Support (Complete - 2026-01-30)
- 📋 Epic 3: Testing Framework (Deferred)
- ✅ Epic 4: Environment Drift Detection (Complete - 2026-01-31)

**Success Criteria:**
- ✅ Rollback support with `.down.sql` execution
- 📋 Comprehensive test suite runs automatically (deferred to future)
- ✅ Drift detection identifies environment discrepancies
- ✅ Confidence in deployment quality (rollback safety + drift detection established)

### Phase 3: Polish & Scale
**Goal:** Production-ready solution

- Epic 5: Developer Experience & Onboarding
- Epic 6: CI/CD & Ephemeral Environments

**Success Criteria:**
- New developer onboarding takes < 15 minutes
- CI/CD pipeline fully automated
- Ephemeral environments for PR testing
- Documentation complete

---

## Current Status

**Active Epic:** None (Phase 2 Complete!)

**Completed Epics:**
- ✅ Epic 0: Container Infrastructure (2026-01-27)
- ✅ Epic 1: Migration Generation System (2026-01-27)
- ✅ Epic 2: Migration Execution & Tracking (2026-01-28)
- ✅ Epic 3: Rollback Support (2026-01-30)
- ✅ Epic 4: Environment Drift Detection (2026-01-31)

**Phase 1 & Phase 2 Complete!** All core migration lifecycle features implemented including generation, execution, rollback, and drift detection. Test coverage: 82 total tests (65 migration tests + 17 drift detection tests). Run with `./test.sh`.

**Next Steps:**
1. Choose next epic to tackle (Phase 3):
   - **Option A:** Epic 3 - Testing Framework (formalize test framework with `dbctl test` command)
   - **Option B:** Epic 5 - Developer Experience improvements (better documentation, error messages, onboarding)
   - **Option C:** Epic 6 - CI/CD & Ephemeral Environments (GitHub Actions, PR databases)

---

## Notes & Decisions Log

### 2026-01-27: Initial Backlog Creation
- Defined container-first architecture
- Selected timestamp-based migrations over sequential numbering
- Prioritized migration generation as first major capability
- Decided to use official Microsoft container images
- Chose Python as primary implementation language
- Target environments: Dev, Staging, Production, plus ephemeral PR environments

### 2026-01-27: Epic 0 Completion - Container Infrastructure
- ✅ Added sqlpackage to dev.Dockerfile as a dotnet global tool
- ✅ Created `dbctl` Python CLI with Click framework
- ✅ Implemented three initial commands: `info`, `build`, `status`
- ✅ Added VS Code tasks for common operations
- ✅ Created GETTING_STARTED.md documentation
- ✅ All operations now run in containers with consistent tooling
- 📝 Note: CLI designed to run inside container; developers use via devcontainer or docker compose exec

### 2026-01-28: Epic 2 Completion - Migration Execution & Tracking
- ✅ Implemented `dbctl migrate` with dry-run support
- ✅ Created `__MigrationsHistory` table for tracking
- ✅ SHA256 checksum validation for tamper detection
- ✅ Application lock (`sp_getapplock`) for concurrency protection
- ✅ Sqlcmd-based execution (replaced initial pyodbc approach)
- ✅ 47/47 tests passing (100% coverage)

**Key Technical Decisions:**
- **Sqlcmd over pyodbc**: Pyodbc created nested transaction conflicts with sqlpackage-generated scripts. Shelling out to sqlcmd preserves proper transaction management.
- **Minimal SQL filtering**: Only remove SQLCMD-specific syntax (`:setvar`, `:on error exit`, `IF $(__IsSqlCmdEnabled)`), don't manipulate migration logic.
- **Named constraints required**: Always use explicit constraint names (e.g., `CONSTRAINT DF_TableName_Column`) to avoid sqlpackage bugs with unnamed constraints.
- **FreeTDS driver**: MacOS uses FreeTDS; removed unsupported TDS features from connection strings.

**Deferred to Epic 3:**
- Rollback support (`dbctl rollback` command) - DOWN migrations are generated but not executable yet

### 2026-01-30: Epic 3 Completion - Rollback Support
- ✅ Implemented `dbctl rollback` with `--force` and `--dry-run` flags
- ✅ Added `RolledBackAt` and `RolledBackBy` columns to `__MigrationsHistory`
- ✅ Created `ensure_rollback_columns()` for backwards compatibility
- ✅ Multi-migration rollback with `--count N` parameter
- ✅ Template `.down.sql` detection (blocks rollback if TODO marker present)
- ✅ Updated `dbctl status` to show rollback information
- ✅ 65/65 tests passing (100% coverage including rollback tests)

**Key Technical Decisions:**
- **Audit trail over deletion**: Rollbacks mark migrations with `RolledBackAt`/`RolledBackBy` instead of deleting rows from history table. Enables rollback analysis and potential re-apply feature.
- **Safety first**: Require `--force` flag for execution (prevents accidental data loss), provide `--dry-run` for safe preview.
- **Reuse proven patterns**: Leveraged Epic 2's sqlcmd execution pattern, lock mechanism, and SQL cleaning logic for consistency.
- **Reverse chronological order**: Always rollback most recent migrations first to prevent dependency violations.
- **Template detection**: Identify `.down.sql` files with TODO markers that require manual implementation before rollback.

### 2026-01-31: Epic 4 Completion - Environment Drift Detection
- ✅ Implemented `dbctl drift` command with comprehensive feature set
- ✅ Created `drift_detector.py` core module with DACPAC extraction and comparison
- ✅ Tolerance levels: strict, normal (default), permissive for acceptable drift
- ✅ Multiple output formats: table, JSON, XML
- ✅ Repair migration generation with `--fix` flag
- ✅ Integration with `dbctl migrate --validate-drift` to block deployments on drift
- ✅ CI/CD ready with `--exit-code` flag
- ✅ 17 integration tests in test-drift.sh

**Key Technical Decisions:**
- **sqlpackage Extract with connection string**: Used `/SourceConnectionString` with `TrustServerCertificate=True` for self-signed cert support (not individual server/database params which don't support TrustServerCertificate).
- **Three tolerance levels**: Strict (any change is drift), normal (allows performance indexes/statistics), permissive (also allows extended properties).
- **Safety-first repairs**: DROP operations automatically commented out in generated repair migrations, requiring manual review before execution.
- **Audit trail focus**: No drift history table initially - keep it simple with file-based reports.
- **Reuse existing patterns**: Leveraged Epic 1's DACPAC comparison, Epic 2's sqlcmd execution, Epic 3's safety-first approach (--force flags, dry-run).
- **Exit codes for CI**: 0=no drift, 1=drift detected, 2=error - perfect for pipeline integration.

### Questions to Resolve
- [x] ~~Specific CLI naming convention~~ → Resolved: `dbctl` (database control)
- [x] ~~VS Code integration approach~~ → Resolved: devcontainer + tasks (both)
- [ ] Test framework choice (pytest, custom, SQL-based) - leaning toward bash scripts + pytest hybrid
- [x] ~~Migration file format~~ → Resolved: pure SQL with metadata headers in comments
- [x] ~~Rollback strategy~~ → Resolved: down migrations (`.down.sql` files)
- [x] ~~Rollback history tracking~~ → Resolved: mark as rolled back with `RolledBackAt`/`RolledBackBy` columns (maintains audit trail)
- [x] ~~Rollback confirmation~~ → Resolved: `--force` flag required for execution, `--dry-run` for preview

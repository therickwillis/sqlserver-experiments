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

### User Stories

- [ ] As a developer, I can run a containerized command to build my SQL project and generate a DACPAC
- [ ] As a developer, I can run a containerized tool to compare DACPACs and detect schema changes
- [ ] As a developer, I can auto-generate a timestamp-based migration script (UP) from detected changes
- [ ] As a developer, I can generate rollback migrations (DOWN) when possible
- [ ] As a developer, I can handle complex migrations (renames, data transformations) with templated scripts
- [ ] As a developer, I can see a migration preview before generating files
- [ ] As a developer, I can track which baseline DACPAC was used for each migration
- [ ] As a developer, migration generation works identically on Windows, Mac, and Linux via containers

### Technical Notes

- Use `sqlpackage` for DACPAC builds and schema comparisons
- Timestamp format: `YYYYMMDDHHMMSS_description.sql` (e.g., `20260127143022_add_bee_species_table.sql`)
- Store baseline DACPAC reference in migration metadata
- Consider edge cases: column renames vs add/drop, table renames, etc.

---

## Epic 2: Migration Execution & Tracking

**Goal:** Apply migrations reliably and track state across environments

**Priority:** High (Required for basic workflow)

### User Stories

- [ ] As a developer, I can apply pending migrations using containerized tooling
- [ ] As a system, I track which migrations have been applied (migrations history table)
- [ ] As a developer, I can see the migration status of any environment through containerized CLI
- [ ] As a developer, I can validate migrations before applying them (dry-run)
- [ ] As a developer, I can rollback the last migration if needed
- [ ] As a developer, I can run migrations in a transaction (when safe)
- [ ] As a CI pipeline, I run the exact same migration container as local development

### Technical Notes

- Create `__MigrationsHistory` table to track applied migrations (timestamp, checksum, applied_at, etc.)
- Support both transactional and non-transactional migrations
- Validate migration checksums to detect tampering
- Lock mechanism to prevent concurrent migrations

---

## Epic 3: Testing Framework

**Goal:** Build confidence in database changes through automated testing

**Priority:** High (Quality gate for deployments)

### User Stories

- [ ] As a developer, I can run all tests in an isolated container environment
- [ ] As a developer, I can define schema validation tests (tables, columns, constraints exist)
- [ ] As a developer, I can define data integrity tests (constraints are enforced)
- [ ] As a developer, I can test that migrations run successfully against test data
- [ ] As a developer, I can test migration rollbacks don't lose data
- [ ] As a developer, I can run all tests with a single containerized command
- [ ] As a developer, I can see clear test results and failures
- [ ] As a CI pipeline, I run the same test container image as local development
- [ ] As a developer, tests run in ephemeral containers that clean up automatically

### Technical Notes

- Consider test frameworks: pytest, custom test runner, or SQL-based tests
- Test types:
  - Schema tests: Assert table/column/constraint existence
  - Data integrity tests: Attempt to violate constraints, ensure failure
  - Migration tests: Apply migrations to test DB, validate success
  - Rollback tests: Apply then rollback, ensure no data loss
- Support test fixtures and seed data for testing

---

## Epic 4: Environment Drift Detection

**Goal:** Prevent and detect schema drift across environments

**Priority:** Medium (Key pain point to solve)

### User Stories

- [ ] As a developer, I can compare two database environments using containerized tools
- [ ] As a developer, I can detect drift between my local DB and the migration scripts
- [ ] As a developer, I can see a report of schema differences between environments
- [ ] As a system, I can block deployments if target environment has unexpected drift
- [ ] As a developer, I can generate a "repair" migration to fix drift
- [ ] As a CI pipeline, I can run drift detection as part of deployment validation

### Technical Notes

- Use `sqlpackage /Action:DeployReport` to generate drift reports
- Compare target environment against:
  1. Expected state from migrations
  2. Source DACPAC
- Configurable drift tolerance (some drift may be acceptable in certain scenarios)
- Generate repair scripts automatically when possible

---

## Epic 5: Developer Experience & Onboarding

**Goal:** Make it simple to get started and work efficiently on any platform

**Priority:** Medium (Reduces friction, increases adoption)

### User Stories

- [ ] As a new developer on any OS, I can run `docker compose up` and have a working environment
- [ ] As a developer, I have a VS Code devcontainer configuration that provides consistent tooling
- [ ] As a developer, I can use VS Code commands/tasks that execute in containers
- [ ] As a developer, I have clear CLI commands for all operations (init, migrate, test, etc.)
- [ ] As a developer, I don't need to install SQL Server tools locally - containers provide everything
- [ ] As a developer, I can see helpful error messages when things go wrong
- [ ] As a developer, I have documentation and examples for common scenarios
- [ ] As a Windows developer, everything works without WSL complexity
- [ ] As a Mac developer with ARM, containers work natively with proper platform support

### Technical Notes

- CLI command structure: `dbctl <command> [options]` (or similar naming)
- Common commands:
  - `init` - Initialize new database project
  - `migrate` - Apply pending migrations
  - `generate` - Generate migration from schema changes
  - `test` - Run test suite
  - `status` - Show migration status
  - `drift` - Detect schema drift
- VS Code integration options:
  - Tasks for common commands
  - Devcontainer for full environment
  - Extension for UI features (future)

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

- Support multiple CI platforms: GitHub Actions, GitLab CI, Azure DevOps, Jenkins
- Ephemeral environment naming: `db-pr-{PR_NUMBER}` or similar
- Consider Azure SQL, AWS RDS, and containerized SQL Server for ephemeral environments
- Deployment safety checks:
  - Run tests before deployment
  - Check for drift
  - Validate migration checksums
  - Optional manual approval gate

---

## Roadmap Phases

### Phase 1: Foundation (Weeks 1-4)
**Goal:** Basic migration generation and execution

- Epic 0: Container Infrastructure (Complete)
- Epic 1: Migration Generation System (Complete)
- Epic 2: Migration Execution & Tracking (Core functionality)

**Success Criteria:**
- Developer can generate migrations from SQL project changes
- Developer can apply migrations to local database
- All operations run in containers

### Phase 2: Quality & Confidence (Weeks 5-8)
**Goal:** Build trust through testing and drift detection

- Epic 3: Testing Framework (Complete)
- Epic 4: Environment Drift Detection (Complete)
- Epic 2: Migration Execution & Tracking (Rollback functionality)

**Success Criteria:**
- Comprehensive test suite runs automatically
- Drift detection identifies environment discrepancies
- Confidence in deployment quality

### Phase 3: Polish & Scale (Weeks 9-12)
**Goal:** Production-ready solution

- Epic 5: Developer Experience & Onboarding (Complete)
- Epic 6: CI/CD & Ephemeral Environments (Complete)

**Success Criteria:**
- New developer onboarding takes < 15 minutes
- CI/CD pipeline fully automated
- Ephemeral environments for PR testing
- Documentation complete

---

## Current Status

**Active Epic:** Epic 1 - Migration Generation System

**Completed Epics:**
- ✅ Epic 0: Container Infrastructure (2026-01-27)

**Next Steps:**
1. Begin Epic 1: Migration Generation System
   - Implement DACPAC comparison functionality
   - Create migration script generation logic
   - Build timestamp-based migration file naming
2. Continue to Epic 2: Migration Execution & Tracking

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

### Questions to Resolve
- [ ] Specific CLI naming convention (dbctl, sqlmigrate, etc.)
- [ ] VS Code integration approach (devcontainer vs tasks vs extension)
- [ ] Test framework choice (pytest, custom, SQL-based)
- [ ] Migration file format (pure SQL, with metadata headers, separate metadata file)
- [ ] Rollback strategy (down migrations, snapshot/restore, schema version table)

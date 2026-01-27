# Cross-Platform SQL Server Architecture

This document describes the architectural decisions and implementation details for supporting SQL Server development across x86_64 (AMD64) and ARM64 (Apple Silicon) platforms.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Architecture Decision](#architecture-decision)
- [Cross-Platform Implementation](#cross-platform-implementation)
- [Development Guidelines](#development-guidelines)
- [Verification](#verification)

---

## Problem Statement

SQL Server 2022 does not natively support ARM64 architecture (Apple Silicon Macs). When attempting to run the official `mcr.microsoft.com/mssql/server:2022-latest` Docker image on ARM64 hosts, the container fails with memory mapping errors under QEMU emulation:

```
/opt/mssql/bin/sqlservr: Invalid mapping of address 0x400434a000 in reserved address space
```

This creates a development environment challenge: developers on Mac (ARM64) cannot run the same SQL Server version as production environments (typically Windows/Intel with SQL Server 2022).

### SQL Server Version Differences

- **SQL Server 2022** (v16.x): Latest production version with modern features
- **Azure SQL Edge** (v15.x): Based on SQL Server 2019 engine, ARM64-compatible
- **Version Gap**: Azure SQL Edge lacks SQL Server 2022 features and has engine differences

### Missing in Azure SQL Edge

Azure SQL Edge is designed for IoT/edge scenarios and lacks several enterprise features:

- SQL Server Agent (scheduled jobs, maintenance plans)
- Full-text search
- SQL Server Reporting Services (SSRS)
- SQL Server Integration Services (SSIS)
- SQL Server Analysis Services (SSAS)
- Replication, PolyBase, Machine Learning Services
- Some SQL Server 2022 features (Ledger tables, Parameter Sensitive Plan optimization, etc.)

### What Azure SQL Edge Includes

- Core database engine (SQL 2019 based)
- T-SQL support (most common features)
- ONNX machine learning support
- Data streaming capabilities
- Time-series functions
- Compatible with most OLTP workloads

---

## Architecture Decision

### Options Considered

#### Option 1: Azure SQL Edge Only
- **Pros**: Native ARM64 performance, fast and stable
- **Cons**: Development-production version mismatch, missing features

#### Option 2: Force x64 Emulation
- **Pros**: Exact production parity, all SQL Server 2022 features
- **Cons**: Slow, high memory usage, container instability

#### Option 3: Remote Development
- **Pros**: True production parity, no local resources
- **Cons**: Network dependency, additional cost, slower feedback

#### Option 4: Hybrid Approach ✅ **CHOSEN**
- **Pros**: Fast local development + production parity validation, flexibility per environment
- **Cons**: Requires discipline to test on real version, maintain both configs

### Decision Rationale

We've chosen the **Hybrid Approach** as the best balance of development speed and production parity:

- Fast local development experience on Mac with Azure SQL Edge
- Production validation available via SQL Server 2022 in CI/CD
- Flexibility for each developer/environment
- CI/CD uses real SQL Server 2022 for integration tests

---

## Cross-Platform Implementation

### What Works on Each Architecture

#### x86_64 (Windows, Linux, Intel Macs)

All tools natively supported:
- ✅ .NET SDK 8.0
- ✅ sqlpackage (via dotnet tool)
- ✅ sqlcmd (Microsoft mssql-tools)
- ✅ Microsoft ODBC Driver 18 for SQL Server
- ✅ Python 3 + pyodbc

#### ARM64 (Apple Silicon M1/M2/M3/M4)

ARM64 alternatives:
- ✅ .NET SDK 8.0 (native ARM64)
- ✅ sqlpackage (via dotnet tool, native ARM64)
- ✅ sqlcmd (go-sqlcmd, cross-platform alternative)
- ✅ FreeTDS ODBC driver (for pyodbc connectivity)
- ✅ Python 3 + pyodbc

### Key Implementation Differences

#### ODBC Driver

**x86_64:**
- Uses Microsoft ODBC Driver 18/17 for SQL Server
- Connection string: `DRIVER={ODBC Driver 18 for SQL Server};...`

**ARM64:**
- Uses FreeTDS ODBC driver
- Connection string: `DRIVER={FreeTDS};...`
- Python code automatically detects and uses the available driver

#### sqlcmd

**x86_64:**
- Microsoft's native sqlcmd from mssql-tools
- Located at `/opt/mssql-tools/bin/sqlcmd`

**ARM64:**
- go-sqlcmd (Microsoft's cross-platform alternative)
- Compatible with the same commands and flags
- Located at `/usr/local/bin/sqlcmd`

#### SQL Server Container

**Environment-based image selection** in `docker-compose.yml`:

```yaml
sqlserver:
  image: ${SQL_IMAGE:-mcr.microsoft.com/mssql/server:2022-latest}
```

**Mac (ARM64) - .env:**
```bash
SQL_IMAGE=mcr.microsoft.com/azure-sql-edge:latest
MSSQL_PID=Developer
```

**Windows/Intel (AMD64) - .env:**
```bash
SQL_IMAGE=mcr.microsoft.com/mssql/server:2022-latest
MSSQL_PID=Developer
```

**CI/CD Environments:**
```bash
SQL_IMAGE=mcr.microsoft.com/mssql/server:2022-latest
MSSQL_PID=Developer
```

### No Manual Configuration Required

The entire setup is architecture-aware:
- Dockerfile detects architecture at build time
- Python code auto-detects available ODBC driver
- sqlcmd provided via appropriate method for platform
- Docker Compose uses environment variables for SQL Server image

---

## Development Guidelines

### For Mac (ARM64) Developers

1. **Daily Development**: Use Azure SQL Edge for fast iteration
2. **Feature Testing**: Test SQL Server-specific features on real 2022 instance
3. **Pre-Commit**: Run integration tests against SQL Server 2022 (CI/CD or remote)
4. **Avoid Edge-Only Features**: Don't rely on Azure SQL Edge streaming or time-series features

### Compatibility Best Practices

#### 1. Target SQL Server 2019 Compatibility Level

```sql
ALTER DATABASE EnchantedBeesDB SET COMPATIBILITY_LEVEL = 150;
```

This ensures features work on both Azure SQL Edge and SQL Server 2022.

#### 2. Avoid Version-Specific Features

- Don't use SQL Server 2022-only syntax unless explicitly required
- Document any SQL 2022-specific features used
- Test on real SQL Server 2022 before production

#### 3. Test on Real SQL Server 2022

- CI/CD should run against SQL Server 2022
- Pre-production validation required
- Integration tests against real version

#### 4. Check for Missing Features

- No SQL Server Agent jobs (use external schedulers like cron, Kubernetes CronJobs)
- No full-text search (use application-level search or alternatives)
- Test replication/advanced features on real SQL Server

---

## Verification

### Quick Environment Check

Run inside the dev container:

```bash
echo "Architecture: $(uname -m)"
dotnet --version
sqlpackage /version
sqlcmd -?
python3 -c "import pyodbc; print('ODBC Drivers:'); print('\n'.join(pyodbc.drivers()))"
```

**Expected output on x86_64:**
```
Architecture: x86_64
8.0.417
170.2.70.1
Microsoft (R) SQL Server Command Line Tool...
ODBC Drivers:
ODBC Driver 18 for SQL Server
ODBC Driver 17 for SQL Server
```

**Expected output on ARM64:**
```
Architecture: aarch64
8.0.417
170.2.70.1
sqlcmd: command line tool for SQL Server...
ODBC Drivers:
FreeTDS
```

### Check SQL Server Version

```sql
SELECT @@VERSION;
```

**Azure SQL Edge Output:**
```
Microsoft Azure SQL Edge Developer (RTM) - 15.0.2000.1574 (ARM64)
```

**SQL Server 2022 Output:**
```
Microsoft SQL Server 2022 (RTM) - 16.0.1000.6 (X64)
```

**From Command Line:**
```bash
# Inside dev container
sqlcmd -S sqlserver -U sa -P "${SA_PASSWORD}" -Q "SELECT @@VERSION" -No
```

### Testing Your Setup

```bash
# Build for your native architecture
docker-compose build dev

# Start services
docker-compose up -d

# Access dev container
docker-compose exec dev bash

# Inside container: verify everything
./dbctl info
```

---

## Migration Path

If production moves to ARM64 in the future, or if Microsoft releases SQL Server 2022 for ARM64:

1. Update `SQL_IMAGE` in `.env.example`
2. Update this document
3. Announce to team
4. Rebuild containers: `docker-compose down && docker-compose up --build -d`

---

## Resources

- [Azure SQL Edge Documentation](https://learn.microsoft.com/en-us/azure/azure-sql-edge/)
- [SQL Server 2022 Features](https://learn.microsoft.com/en-us/sql/sql-server/what-s-new-in-sql-server-2022)
- [Docker SQL Server Images](https://hub.docker.com/_/microsoft-mssql-server)
- [go-sqlcmd GitHub](https://github.com/microsoft/go-sqlcmd)
- [FreeTDS Project](https://www.freetds.org/)

---

## Revision History

- **2026-01-26**: Initial decision document created, consolidated from two separate docs
- **Decision Owner**: Development Team
- **Next Review**: When SQL Server 2022 ARM64 support is announced, or in 6 months

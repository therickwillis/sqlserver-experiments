# SQL Server Architecture Decision: ARM64 Compatibility

## Problem Statement

SQL Server 2022 does not natively support ARM64 architecture (Apple Silicon Macs). When attempting to run the official `mcr.microsoft.com/mssql/server:2022-latest` Docker image on ARM64 hosts, the container fails with memory mapping errors under QEMU emulation:

```
/opt/mssql/bin/sqlservr: Invalid mapping of address 0x400434a000 in reserved address space
```

This creates a development environment challenge: developers on Mac (ARM64) cannot run the same SQL Server version as production environments (typically Windows/Intel with SQL Server 2022).

## Background

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
- Replication
- PolyBase
- Machine Learning Services
- Some SQL Server 2022 features:
  - Ledger tables
  - Contained availability groups
  - Parameter Sensitive Plan optimization
  - Intelligent query processing enhancements

### What Azure SQL Edge Includes

- Core database engine (SQL 2019 based)
- T-SQL support (most common features)
- ONNX machine learning support
- Data streaming capabilities
- Time-series functions
- Compatible with most OLTP workloads

## Options Considered

### Option 1: Accept Azure SQL Edge on Mac

**Approach**: Use Azure SQL Edge for Mac development, SQL Server 2022 elsewhere

**Pros**:
- Native ARM64 performance
- Fast, stable, no emulation overhead
- Works immediately

**Cons**:
- Development-production version mismatch
- Missing features may not be discovered until later
- Potential T-SQL compatibility issues

### Option 2: Force x64 Emulation with Rosetta 2

**Approach**: Use `platform: linux/amd64` to force SQL Server 2022 emulation

**Pros**:
- Exact production parity
- All SQL Server 2022 features available

**Cons**:
- Slow performance (emulation overhead)
- High memory usage
- Container instability (crashes observed)
- Increased battery drain on laptops

### Option 3: Remote Development

**Approach**: Run SQL Server 2022 on remote Windows/Intel machine or cloud VM

**Pros**:
- True production parity
- No local resource consumption

**Cons**:
- Network dependency
- Additional infrastructure cost
- Slower development feedback loop
- VPN/connectivity requirements

### Option 4: Hybrid Approach (CHOSEN)

**Approach**: Use Azure SQL Edge for daily Mac development, SQL Server 2022 for integration testing

**Pros**:
- Fast local development experience
- Production parity validation available
- Flexibility per developer/environment
- CI/CD can use real SQL Server 2022

**Cons**:
- Requires discipline to test on real version
- Potential for late-stage version issues
- Need to maintain both configurations

## Decision: Hybrid Approach

We've chosen the **Hybrid Approach** as the best balance of development speed and production parity.

### Implementation

The `docker-compose.yml` supports environment-based SQL Server image selection:

```yaml
sqlserver:
  # Use Azure SQL Edge for ARM64 (Mac), SQL Server 2022 for AMD64 (Windows/Intel)
  image: ${SQL_IMAGE:-mcr.microsoft.com/mssql/server:2022-latest}
```

### Configuration per Platform

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

## Development Guidelines

### For Mac Developers

1. **Daily Development**: Use Azure SQL Edge for fast iteration
2. **Feature Testing**: Test SQL Server-specific features on real 2022 instance
3. **Pre-Commit**: Run integration tests against SQL Server 2022 (CI/CD or remote)
4. **Avoid Edge-Only Features**: Don't rely on Azure SQL Edge streaming or time-series features

### Compatibility Best Practices

1. **Target SQL Server 2019 Compatibility Level**
   ```sql
   ALTER DATABASE EnchantedBeesDB SET COMPATIBILITY_LEVEL = 150;
   ```
   This ensures features work on both Azure SQL Edge and SQL Server 2022.

2. **Avoid Version-Specific Features**
   - Don't use SQL Server 2022-only syntax unless explicitly required
   - Document any SQL 2022-specific features used

3. **Test on Real SQL Server 2022**
   - CI/CD should run against SQL Server 2022
   - Pre-production validation required
   - Integration tests against real version

4. **Check for Missing Features**
   - No SQL Server Agent jobs (use external schedulers)
   - No full-text search (use application-level search or alternatives)
   - Test replication/advanced features on real SQL Server

## Verification

### Check Your SQL Server Version

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

### From Command Line

```bash
# Inside dev container
sqlcmd -S sqlserver -U sa -P "${PASSWORD}" -Q "SELECT @@VERSION" -No
```

## Migration Path

If production moves to ARM64 in the future, or if Microsoft releases SQL Server 2022 for ARM64:

1. Update `SQL_IMAGE` in `.env.example`
2. Update this document
3. Announce to team
4. Rebuild containers: `docker-compose down && docker-compose up --build -d`

## Resources

- [Azure SQL Edge Documentation](https://learn.microsoft.com/en-us/azure/azure-sql-edge/)
- [SQL Server 2022 Features](https://learn.microsoft.com/en-us/sql/sql-server/what-s-new-in-sql-server-2022)
- [Docker SQL Server Images](https://hub.docker.com/_/microsoft-mssql-server)

## Revision History

- **2026-01-26**: Initial decision document created
- **Decision Owner**: Development Team
- **Next Review**: When SQL Server 2022 ARM64 support is announced, or in 6 months

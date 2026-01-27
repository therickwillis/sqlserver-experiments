# Cross-Architecture Support

This project supports both **x86_64 (amd64)** and **ARM64 (Apple Silicon)** architectures.

## What Works on Each Architecture

### x86_64 (Windows, Linux, Intel Macs)

All tools are natively supported:
- ✅ .NET SDK 8.0
- ✅ sqlpackage (via dotnet tool)
- ✅ sqlcmd (Microsoft mssql-tools)
- ✅ Microsoft ODBC Driver 18 for SQL Server
- ✅ Python 3 + pyodbc

### ARM64 (Apple Silicon M1/M2/M3)

Tools with ARM64 alternatives:
- ✅ .NET SDK 8.0 (native ARM64)
- ✅ sqlpackage (via dotnet tool, native ARM64)
- ✅ sqlcmd (go-sqlcmd, cross-platform alternative)
- ✅ FreeTDS ODBC driver (for pyodbc connectivity)
- ✅ Python 3 + pyodbc

## Key Differences

### ODBC Driver

**x86_64:**
- Uses Microsoft ODBC Driver 18/17 for SQL Server
- Connection string: `DRIVER={ODBC Driver 18 for SQL Server};...`

**ARM64:**
- Uses FreeTDS ODBC driver
- Connection string: `DRIVER={FreeTDS};...`
- The Python code automatically detects and uses the available driver

### sqlcmd

**x86_64:**
- Uses Microsoft's native sqlcmd from mssql-tools
- Located at `/opt/mssql-tools/bin/sqlcmd`

**ARM64:**
- Uses go-sqlcmd (Microsoft's cross-platform alternative)
- Compatible with the same commands and flags
- Located at `/usr/local/bin/sqlcmd`

## SQL Server Container

The SQL Server container image (`mcr.microsoft.com/mssql/server:2022-latest`) is **x86_64 only**. On ARM64 systems, it runs under Rosetta 2 emulation via Docker Desktop.

To force platform emulation in docker-compose.yml:
```yaml
sqlserver:
  platform: linux/amd64
  image: mcr.microsoft.com/mssql/server:2022-latest
```

**Note:** For native ARM64 SQL Server, consider using Azure SQL Edge:
```yaml
sqlserver:
  image: mcr.microsoft.com/azure-sql-edge:latest
```

## Testing on Your Mac

The dev container should build and run without any special configuration:

```bash
# Build for your native architecture
docker-compose build dev

# Start the services
docker-compose up -d

# Access the dev container
docker-compose exec dev bash
```

## Verifying Your Setup

Run this inside the dev container to check your environment:

```bash
echo "Architecture: $(uname -m)"
dotnet --version
sqlpackage /version
sqlcmd -?
python3 -c "import pyodbc; print('ODBC Drivers:'); print('\n'.join(pyodbc.drivers()))"
```

Expected output on **x86_64**:
```
Architecture: x86_64
8.0.417
170.2.70.1
Microsoft (R) SQL Server Command Line Tool...
ODBC Drivers:
ODBC Driver 18 for SQL Server
ODBC Driver 17 for SQL Server
```

Expected output on **ARM64**:
```
Architecture: aarch64
8.0.417
170.2.70.1
sqlcmd: command line tool for SQL Server...
ODBC Drivers:
FreeTDS
```

## No Surprises, Just Works

The entire setup is architecture-aware:
- The Dockerfile detects your architecture at build time
- Python code auto-detects the available ODBC driver
- sqlcmd is provided via the appropriate method for your platform
- No manual configuration needed

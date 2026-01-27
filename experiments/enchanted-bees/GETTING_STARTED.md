# Getting Started with dbctl

## Overview

`dbctl` is a containerized database management CLI that works identically on Windows, Mac, and Linux. All operations run inside Docker containers for complete environment parity between development and CI/CD.

## Prerequisites

- Docker and Docker Compose
- VS Code with Remote-Containers extension (recommended)

## Quick Start

> **Important:** If you're updating from a previous version, rebuild the dev container to get the latest tooling:
> ```bash
> docker compose build dev --no-cache
> docker compose up -d
> ```

### Option 1: Using VS Code Dev Container (Recommended)

1. Open this project in VS Code
2. When prompted, click "Reopen in Container" (or run command: "Remote-Containers: Reopen in Container")
   - If updating, use "Remote-Containers: Rebuild Container" instead
3. Wait for the container to build and start
4. Open a terminal in VS Code - you're now inside the dev container!

### Option 2: Using Docker Compose

```bash
# Start the SQL Server and dev containers
docker compose up -d

# Execute commands in the dev container
docker compose exec dev /workspace/dbctl info
```

## Using dbctl

### Command Line

From within the dev container terminal:

```bash
# Show environment and tooling information
./dbctl info

# Build SQL project and generate DACPAC
./dbctl build

# Show database status
./dbctl status
```

### VS Code Tasks

Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux) and type "Tasks: Run Task", then choose:

- **dbctl: Info** - Show environment information
- **dbctl: Build** - Build SQL project (default build task: `Cmd+Shift+B`)
- **dbctl: Status** - Show database status
- **dbctl: Build and Publish (Legacy)** - Use the old publish script

## Available Commands

### `dbctl info`

Displays environment information including:
- System platform and Python version
- Database connection configuration
- Installed tool versions (dotnet, sqlpackage, sqlcmd)

### `dbctl build`

Builds the SQL Server project and generates a DACPAC artifact.

**Options:**
- `--project, -p`: Path to SQL project file (default: EnchantedBeesDB/EnchantedBeesDB.sqlproj)
- `--configuration, -c`: Build configuration (default: Debug)

**Example:**
```bash
./dbctl build --configuration Release
```

### `dbctl status`

Shows database connection status and tests connectivity.

**Checks:**
- Database server reachability
- Whether target database exists
- Migration status (coming in Epic 1)

## Container Architecture

The project uses two containers:

1. **sqlserver**: Microsoft SQL Server 2022 Developer Edition
   - Accessible on port defined in `.env` (default: 1433)
   - Data persists in Docker volume `mssql_data`

2. **dev**: Development tooling container
   - Includes: .NET SDK, Python, sqlpackage, sqlcmd, ODBC drivers
   - Mounts workspace for live code changes
   - Runs as non-root `dev` user

## Environment Variables

Configuration is managed through environment variables:

```bash
# Database connection (set in docker-compose.yml)
DB_SERVER=sqlserver
DB_PORT=1433
DB_NAME=EnchantedBeesDB
DB_USER=sa
DB_PASSWORD=<from .env file>

# Dev mode (enables auto-install of requirements)
DEV_MODE=1
```

## Next Steps

- **Epic 1**: Learn about migration generation (coming soon)
- **Epic 2**: Learn about migration execution (coming soon)
- **Epic 3**: Learn about the testing framework (coming soon)

## Troubleshooting

### SQL Server not ready

If you see connection errors, SQL Server may still be starting. Wait 30-60 seconds and try again.

### sqlpackage not found

If `dbctl info` shows "sqlpackage: Not found", you need to rebuild the dev container:

```bash
# Rebuild the dev container with updated dependencies
docker compose build dev --no-cache
docker compose up -d dev
```

### Permission issues

The dev container runs as the `dev` user with UID/GID matching your host user (default: 1000). If you see permission issues, check the `USER_ID` and `GROUP_ID` in your `.env` file.

## Help

For more information:
- See [BACKLOG.md](BACKLOG.md) for the product roadmap
- See [README.md](README.md) for project overview
- Run `./dbctl --help` for CLI usage

# Enchanted Bees

This is an experiment inspired by my lovely wife's Ark mod.

## Goals
* Create a Database for managing her mod data
* Create a simple UI for her to access the information
* Use the data to create visual assets for sharing Bee info

## Tools
* SQL Server Database Projects
* SSDT

## Development Environment

This project uses Docker Compose to provide a consistent development environment with SQL Server and development tools.

### Quick Start

1. Copy `.env.example` to `.env` and adjust settings if needed
2. Start the environment: `docker-compose up -d`
3. Access the dev container: `docker-compose exec dev bash`
4. Use the `dbctl` CLI tool for database operations

### Architecture Notes

**Important**: This project uses different SQL Server versions depending on your host architecture:
- **Mac (ARM64)**: Azure SQL Edge (SQL 2019 engine)
- **Windows/Intel (AMD64)**: SQL Server 2022

See [docs/SQL_SERVER_ARCHITECTURE.md](docs/SQL_SERVER_ARCHITECTURE.md) for details on this decision and development guidelines.

# Enchanted Bees

A practical experiment in modern SQL Server development workflows, cross-platform tooling, and database project management.

## What This Project Is About

This is a hands-on exploration of SQL Server Database Projects (SSDT) in a cross-platform development environment. The project tackles real-world challenges like:

* **Cross-platform SQL Server development** - Working seamlessly across ARM64 (Mac) and AMD64 (Windows/Intel) architectures
* **Database-as-code workflows** - Managing schema, migrations, and deployments through version control
* **Development tooling** - Building CLI tools for database operations and automation
* **Modern DevOps practices** - Containerized development environments with Docker Compose

The example database (managing data for an Ark mod's bee genetics system) provides a fun, realistic use case with interesting relational data patterns - but the real focus is learning and refining the development workflow itself.

## Key Technologies

* SQL Server Database Projects (SSDT/SqlProj)
* Docker Compose for environment management
* Python CLI tooling
* Cross-architecture SQL Server (SQL Server 2022 / Azure SQL Edge)

## Development Environment

This project uses Docker Compose to provide a consistent development environment with SQL Server and development tools.

### Quick Start

1. Copy `.env.example` to `.env` and adjust settings if needed
2. Start the environment: `docker-compose up -d`
3. Initialize the database: `docker compose exec dev dbctl init`
4. Access the dev container: `docker-compose exec dev bash`
5. Use the `dbctl` CLI tool for database operations

### dbctl Commands

The `dbctl` CLI provides all database management operations:

- `dbctl info` - Show environment and tooling information
- `dbctl init` - Initialize and publish database to SQL Server
- `dbctl build` - Build SQL project and generate DACPAC
- `dbctl generate` - Generate migration scripts from schema changes
- `dbctl status` - Show database and migration status

Run tests: `./test.sh`

### Cross-Platform Architecture

This project demonstrates solving real cross-platform challenges:
- **Mac (ARM64)**: Uses Azure SQL Edge (SQL 2019 engine)
- **Windows/Intel (AMD64)**: Uses SQL Server 2022

Both environments maintain compatibility through careful feature selection and testing. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete architectural decisions and implementation details.

### Documentation

- [Getting Started Guide](docs/GETTING_STARTED.md) - Detailed setup and usage instructions
- [Testing Guide](docs/TESTING.md) - Test suite and quality assurance
- [Architecture](docs/ARCHITECTURE.md) - Cross-platform design decisions and implementation details
- [Development Container Setup](docs/DEV_CONTAINER.md) - Container environment details
- [Project Backlog](docs/BACKLOG.md) - Feature roadmap and experiments

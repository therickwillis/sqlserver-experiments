#!/usr/bin/env python3
"""
dbctl CLI - Main entry point for database management commands
"""

import click
import os
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """
    dbctl - Database Management CLI

    Manage MSSQL databases through containerized operations.
    Works identically on Windows, Mac, and Linux.
    """
    ctx.ensure_object(dict)

    # Set workspace root
    ctx.obj['WORKSPACE_ROOT'] = Path('/workspace')


@cli.command()
@click.option('--project', '-p', default='databases/EnchantedBeesDB/EnchantedBeesDB.sqlproj',
              help='Path to SQL project file relative to workspace')
@click.option('--configuration', '-c', default='Debug',
              help='Build configuration (Debug/Release)')
@click.pass_context
def build(ctx, project, configuration):
    """Build SQL project and generate DACPAC"""
    from .commands import build_command
    build_command.build(ctx, project, configuration)


@cli.command()
@click.pass_context
def status(ctx):
    """Show database and migration status"""
    from .commands import status_command
    status_command.status(ctx)


@cli.command()
@click.pass_context
def info(ctx):
    """Show environment and tooling information"""
    from .commands import info_command
    info_command.info(ctx)


@cli.command()
@click.option('--project', '-p', default='databases/EnchantedBeesDB/EnchantedBeesDB.sqlproj',
              help='Path to SQL project file relative to workspace')
@click.option('--configuration', '-c', default='Debug',
              help='Build configuration (Debug/Release)')
@click.option('--server', '-s', default=lambda: os.getenv('DB_SERVER', 'sqlserver'),
              help='SQL Server hostname (default: $DB_SERVER or sqlserver)')
@click.option('--database', '-d', default=lambda: os.getenv('DB_NAME', 'EnchantedBeesDB'),
              help='Database name (default: $DB_NAME or EnchantedBeesDB)')
@click.option('--user', '-u', default=lambda: os.getenv('DB_USER', 'sa'),
              help='SQL Server username (default: $DB_USER or sa)')
@click.option('--password', default=lambda: os.getenv('DB_PASSWORD', ''),
              help='SQL Server password (default: $DB_PASSWORD)')
@click.pass_context
def init(ctx, project, configuration, server, database, user, password):
    """Initialize and publish database to SQL Server"""
    from .commands import init_command
    init_command.init(ctx, project, configuration, server, database, user, password)


@cli.command()
@click.option('--project', '-p', default='databases/EnchantedBeesDB/EnchantedBeesDB.sqlproj',
              help='Path to SQL project file relative to workspace')
@click.option('--configuration', '-c', default='Debug',
              help='Build configuration (Debug/Release)')
@click.option('--message', '-m', default=None,
              help='Custom migration description (auto-generated if not provided)')
@click.option('--init', is_flag=True,
              help='Initialize baseline without generating migration')
@click.pass_context
def generate(ctx, project, configuration, message, init):
    """Generate migration scripts from SQL project changes"""
    from .commands import generate_command
    generate_command.generate(ctx, project, configuration, message, init)


@cli.command()
@click.option('--server', '-s', default=lambda: os.getenv('DB_SERVER', 'sqlserver'),
              help='SQL Server hostname (default: $DB_SERVER or sqlserver)')
@click.option('--database', '-d', default=lambda: os.getenv('DB_NAME', 'EnchantedBeesDB'),
              help='Database name (default: $DB_NAME or EnchantedBeesDB)')
@click.option('--user', '-u', default=lambda: os.getenv('DB_USER', 'sa'),
              help='SQL Server username (default: $DB_USER or sa)')
@click.option('--password', default=lambda: os.getenv('DB_PASSWORD', ''),
              help='SQL Server password (default: $DB_PASSWORD)')
@click.option('--dry-run', is_flag=True,
              help='Show pending migrations without applying them')
@click.option('--validate-drift', is_flag=True,
              help='Check for schema drift before applying migrations')
@click.option('--force', is_flag=True,
              help='Apply migrations even if drift is detected (use with --validate-drift)')
@click.pass_context
def migrate(ctx, server, database, user, password, dry_run, validate_drift, force):
    """Apply pending migrations to database"""
    from .commands import migrate_command
    migrate_command.migrate(ctx, server, database, user, password, dry_run, validate_drift, force)


@cli.command()
@click.option('--count', '-n', type=int, default=1,
              help='Number of migrations to rollback (default: 1)')
@click.option('--server', '-s', default=lambda: os.getenv('DB_SERVER', 'sqlserver'),
              help='SQL Server hostname (default: $DB_SERVER or sqlserver)')
@click.option('--database', '-d', default=lambda: os.getenv('DB_NAME', 'EnchantedBeesDB'),
              help='Database name (default: $DB_NAME or EnchantedBeesDB)')
@click.option('--user', '-u', default=lambda: os.getenv('DB_USER', 'sa'),
              help='SQL Server username (default: $DB_USER or sa)')
@click.option('--password', default=lambda: os.getenv('DB_PASSWORD', ''),
              help='SQL Server password (default: $DB_PASSWORD)')
@click.option('--dry-run', is_flag=True,
              help='Preview rollback without executing')
@click.option('--force', is_flag=True,
              help='Execute rollback without confirmation (required unless --dry-run)')
@click.pass_context
def rollback(ctx, count, server, database, user, password, dry_run, force):
    """Rollback the last N migrations using .down.sql files"""
    from .commands import rollback_command
    rollback_command.rollback(ctx, count, server, database, user, password, dry_run, force)


@cli.command()
@click.option('--server', '-s', default=lambda: os.getenv('DB_SERVER', 'sqlserver'),
              help='SQL Server hostname (default: $DB_SERVER or sqlserver)')
@click.option('--database', '-d', default=lambda: os.getenv('DB_NAME', 'EnchantedBeesDB'),
              help='Database name (default: $DB_NAME or EnchantedBeesDB)')
@click.option('--user', '-u', default=lambda: os.getenv('DB_USER', 'sa'),
              help='SQL Server username (default: $DB_USER or sa)')
@click.option('--password', default=lambda: os.getenv('DB_PASSWORD', ''),
              help='SQL Server password (default: $DB_PASSWORD)')
@click.option('--project', '-p', default='databases/EnchantedBeesDB/EnchantedBeesDB.sqlproj',
              help='Path to SQL project file relative to workspace')
@click.option('--configuration', '-c', default='Debug',
              help='Build configuration (Debug/Release)')
@click.option('--baseline', default=None,
              help='Compare against specific baseline DACPAC instead of project')
@click.option('--output', '-o', default='table', type=click.Choice(['table', 'json', 'xml']),
              help='Output format (default: table)')
@click.option('--report-file', default=None,
              help='Save detailed report to file')
@click.option('--dry-run', is_flag=True,
              help='Show what would be checked without connecting to database')
@click.option('--fix', is_flag=True,
              help='Generate repair migration script to fix detected drift')
@click.option('--tolerance', default='normal', type=click.Choice(['strict', 'normal', 'permissive']),
              help='Drift tolerance level (default: normal)')
@click.option('--exit-code', is_flag=True,
              help='Return non-zero exit code if drift detected (for CI/CD)')
@click.pass_context
def drift(ctx, server, database, user, password, project, configuration,
          baseline, output, report_file, dry_run, fix, tolerance, exit_code):
    """Detect schema drift between database and SQL project"""
    from .commands import drift_command
    drift_command.drift(ctx, server, database, user, password, project,
                       configuration, baseline, output, report_file,
                       dry_run, fix, tolerance, exit_code)


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == '__main__':
    main()

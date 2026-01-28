"""
Migrate command - Apply pending migrations to database
"""

import click
import pyodbc
from pathlib import Path

from ..migration_tracker import (
    get_connection_string,
    ensure_migrations_history_table
)
from ..migration_executor import (
    discover_migrations,
    get_pending_migrations,
    validate_migration_integrity,
    execute_pending_migrations
)


def migrate(ctx, server: str, database: str, user: str, password: str, dry_run: bool):
    """
    Apply pending migrations to the database

    This command:
    1. Connects to the target database
    2. Ensures __MigrationsHistory table exists
    3. Discovers all migration files
    4. Validates migration integrity (no tampering)
    5. Executes pending migrations in order
    6. Records successful migrations

    With --dry-run, shows pending migrations without applying them.
    """
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    migrations_dir = workspace_root / 'migrations'

    click.secho("=" * 60, fg="cyan")
    click.secho("  Database Migration", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    # Step 1: Connect to database
    click.secho("Step 1: Connecting to database...", fg="cyan", bold=True)
    click.echo(f"  Server: {server}")
    click.echo(f"  Database: {database}")
    click.echo(f"  User: {user}")
    click.echo()

    try:
        conn_string = get_connection_string(server, database, user, password)
        # Use autocommit=True since migrations are executed via sqlcmd (which handles transactions)
        # This connection is only used for querying migration status and recording applied migrations
        conn = pyodbc.connect(conn_string, autocommit=True)
    except Exception as e:
        click.secho(f"✗ Connection failed: {e}", fg="red", err=True)
        raise click.Abort()

    try:
        click.secho("✓ Connected successfully", fg="green")
        click.echo()

        # Step 2: Ensure migrations history table exists
        click.secho("Step 2: Initializing migration tracking...", fg="cyan", bold=True)
        ensure_migrations_history_table(conn)
        click.secho("✓ Migration history table ready", fg="green")
        click.echo()

        # Step 3: Discover migrations
        click.secho("Step 3: Discovering migrations...", fg="cyan", bold=True)
        all_migrations = discover_migrations(migrations_dir)
        pending_migrations = get_pending_migrations(migrations_dir, conn)

        click.echo(f"  Total migrations: {len(all_migrations)}")
        click.echo(f"  Applied: {len(all_migrations) - len(pending_migrations)}")
        click.echo(f"  Pending: {len(pending_migrations)}")
        click.echo()

        if len(pending_migrations) == 0:
            click.secho("✓ No pending migrations", fg="green")
            click.echo()
            click.echo("Database is up to date!")
            return

        # Step 4: Validate integrity
        click.secho("Step 4: Validating migration integrity...", fg="cyan", bold=True)
        valid, errors = validate_migration_integrity(migrations_dir, conn)

        if not valid:
            click.secho("✗ Migration integrity check failed!", fg="red", err=True)
            click.echo()
            for error in errors:
                click.secho(f"  {error}", fg="red", err=True)
            click.echo()
            click.echo("DO NOT proceed. Investigate the changes before applying migrations.")
            raise click.Abort()

        click.secho("✓ All migrations validated", fg="green")
        click.echo()

        # Step 5: Show pending migrations
        click.secho("Step 5: Pending migrations:", fg="cyan", bold=True)
        for migration in pending_migrations:
            click.echo(f"  • {migration['migration_id']}")
            click.echo(f"    {migration['description'].replace('_', ' ').title()}")
        click.echo()

        if dry_run:
            click.secho("DRY RUN - No migrations will be applied", fg="yellow", bold=True)
            click.echo()
            click.echo(f"Would apply {len(pending_migrations)} migration(s).")
            return

        # Step 6: Apply migrations
        click.secho("Step 6: Applying migrations...", fg="cyan", bold=True)
        click.echo()

        result = execute_pending_migrations(migrations_dir, conn, dry_run=False)

        # Show results
        for mig in result['migrations']:
            if mig['status'] == 'applied':
                click.secho(f"  ✓ {mig['migration_id']}", fg="green")
                click.echo(f"    Executed in {mig['execution_time_ms']}ms")
            else:
                click.secho(f"  ✗ {mig['migration_id']}", fg="red", err=True)
                click.echo(f"    Error: {mig['error']}", err=True)

        click.echo()

        # Summary
        click.secho("=" * 60, fg="cyan")

        if result['failed_count'] > 0:
            click.secho("  Migration Failed!", fg="red", bold=True, err=True)
            click.secho("=" * 60, fg="cyan")
            click.echo()
            click.echo(f"Applied: {result['applied_count']}/{result['pending_count']}")
            click.echo(f"Failed:  {result['failed_count']}")
            click.echo()
            click.echo("The database transaction was rolled back.")
            click.echo("Fix the error and run 'dbctl migrate' again.")
            raise click.Abort()
        else:
            click.secho("  Migration Complete!", fg="green", bold=True)
            click.secho("=" * 60, fg="cyan")
            click.echo()
            click.echo(f"Successfully applied {result['applied_count']} migration(s).")
            click.echo()
            click.echo("Database is now up to date!")

    finally:
        conn.close()

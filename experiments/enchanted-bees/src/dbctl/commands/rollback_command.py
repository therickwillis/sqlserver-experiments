"""
Rollback command - Rollback migrations using .down.sql files
"""

import click
import pyodbc
from pathlib import Path

from ..migration_tracker import (
    get_connection_string,
    ensure_migrations_history_table,
    ensure_rollback_columns
)
from ..rollback_executor import (
    get_rollbackable_migrations,
    execute_rollbacks
)


def rollback(ctx, count: int, server: str, database: str, user: str, password: str,
             dry_run: bool, force: bool):
    """
    Rollback the last N migrations using .down.sql files

    This command:
    1. Connects to the target database
    2. Ensures __MigrationsHistory table has rollback columns
    3. Gets the last N applied migrations
    4. Validates .down.sql files exist and are executable
    5. Shows preview of rollbacks
    6. Executes rollbacks (if --force is provided or --dry-run)

    With --dry-run, shows what would be rolled back without executing.
    Requires --force flag to execute (prevents accidental data loss).
    """
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    migrations_dir = workspace_root / 'migrations' / database

    click.secho("=" * 60, fg="cyan")
    click.secho("  Database Rollback", fg="cyan", bold=True)
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
        # Use autocommit=True since rollbacks are executed via sqlcmd (which handles transactions)
        conn = pyodbc.connect(conn_string, autocommit=True)
    except Exception as e:
        click.secho(f"✗ Connection failed: {e}", fg="red", err=True)
        raise click.Abort()

    try:
        click.secho("✓ Connected successfully", fg="green")
        click.echo()

        # Step 2: Ensure rollback tracking columns exist
        click.secho("Step 2: Initializing rollback tracking...", fg="cyan", bold=True)
        ensure_migrations_history_table(conn)
        ensure_rollback_columns(conn)
        click.secho("✓ Rollback columns ready", fg="green")
        click.echo()

        # Step 3: Get rollbackable migrations
        click.secho("Step 3: Discovering rollbackable migrations...", fg="cyan", bold=True)
        rollbackable = get_rollbackable_migrations(migrations_dir, conn, count=count)

        if len(rollbackable) == 0:
            click.secho("✓ No migrations available to rollback", fg="yellow")
            click.echo()
            click.echo("The database has no applied migrations that can be rolled back.")
            return

        click.echo(f"  Last {len(rollbackable)} applied migration(s)")
        click.echo()

        # Step 4: Validate down files
        click.secho("Step 4: Validating rollback files...", fg="cyan", bold=True)

        cannot_rollback = []
        for mig in rollbackable:
            if not mig['can_rollback']:
                if not mig['has_down_file']:
                    cannot_rollback.append(
                        f"  ✗ {mig['migration_id']}: .down.sql file not found"
                    )
                elif mig['down_file_is_template']:
                    cannot_rollback.append(
                        f"  ⚠ {mig['migration_id']}: .down.sql is a template requiring manual implementation"
                    )

        if cannot_rollback:
            click.secho("✗ Some migrations cannot be rolled back:", fg="red", err=True)
            click.echo()
            for error in cannot_rollback:
                click.echo(error, err=True)
            click.echo()
            click.echo("Fix the issues above before rolling back.")
            raise click.Abort()

        click.secho("✓ All .down.sql files exist and are executable", fg="green")
        click.echo()

        # Step 5: Show migrations to rollback
        click.secho("Step 5: Migrations to rollback:", fg="cyan", bold=True)
        for mig in rollbackable:
            click.echo(f"  • {mig['migration_id']}")
            click.echo(f"    {mig['description'].replace('_', ' ').title()}")
        click.echo()

        if dry_run:
            click.secho("DRY RUN - No rollbacks will be executed", fg="yellow", bold=True)
            click.echo()
            click.echo(f"Would rollback {len(rollbackable)} migration(s).")
            click.echo()
            click.secho("Use --force to execute rollback.", fg="cyan")
            return

        # Check for --force flag if not dry-run
        if not force:
            click.secho("✗ Missing --force flag", fg="red", err=True)
            click.echo()
            click.echo("Rollback is a destructive operation that may cause data loss.")
            click.echo()
            click.secho("Use --dry-run to preview, or --force to execute rollback.", fg="cyan")
            raise click.Abort()

        # Warning message
        click.secho("⚠ WARNING: This will execute rollback(s). Data may be lost.", fg="yellow", bold=True)
        click.echo()

        # Step 6: Execute rollbacks
        click.secho("Step 6: Executing rollbacks...", fg="cyan", bold=True)
        click.echo()

        result = execute_rollbacks(migrations_dir, conn, count, dry_run=False)

        # Show results
        for rollback_result in result['rollbacks']:
            if rollback_result['status'] == 'rolled_back':
                click.secho(f"  ✓ {rollback_result['migration_id']}", fg="green")
                click.echo(f"    Executed in {rollback_result['execution_time_ms']}ms")
            else:
                click.secho(f"  ✗ {rollback_result['migration_id']}", fg="red", err=True)
                click.echo(f"    Error: {rollback_result['error']}", err=True)

        click.echo()

        # Summary
        click.secho("=" * 60, fg="cyan")

        if result['failed_count'] > 0:
            click.secho("  Rollback Failed!", fg="red", bold=True, err=True)
            click.secho("=" * 60, fg="cyan")
            click.echo()
            click.echo(f"Rolled back: {result['successful_count']}/{result['rollback_count']}")
            click.echo(f"Failed:      {result['failed_count']}")
            click.echo()
            click.echo("The database transaction was rolled back.")
            click.echo("Fix the error and try again.")
            raise click.Abort()
        else:
            click.secho("  Rollback Complete!", fg="green", bold=True)
            click.secho("=" * 60, fg="cyan")
            click.echo()
            click.echo(f"Successfully rolled back {result['successful_count']} migration(s).")
            click.echo()
            click.echo("Database reverted to previous state.")

    finally:
        conn.close()

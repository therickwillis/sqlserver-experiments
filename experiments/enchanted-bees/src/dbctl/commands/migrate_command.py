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


def migrate(ctx, server: str, database: str, user: str, password: str, dry_run: bool, validate_drift: bool = False, force: bool = False):
    """
    Apply pending migrations to the database

    This command:
    1. Connects to the target database
    2. Ensures __MigrationsHistory table exists
    3. Discovers all migration files
    4. Validates migration integrity (no tampering)
    5. (Optional) Validates no drift exists before migration
    6. Executes pending migrations in order
    7. Records successful migrations

    With --dry-run, shows pending migrations without applying them.
    With --validate-drift, checks for schema drift before applying migrations.
    With --force, applies migrations even if drift is detected (requires --validate-drift).
    """
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    migrations_dir = workspace_root / 'migrations' / database

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

        # Step 4.5: Validate drift (optional)
        if validate_drift:
            click.secho("Step 4.5: Checking for schema drift...", fg="cyan", bold=True)

            from ..drift_detector import (
                extract_database_dacpac,
                compare_database_to_project,
                categorize_drift,
                ToleranceLevel
            )
            import tempfile
            import subprocess

            # Build project DACPAC
            project_path = workspace_root / 'databases' / database / f'{database}.sqlproj'

            if not project_path.exists():
                click.secho(f"⚠ Project file not found: {project_path}", fg="yellow")
                click.echo("  Skipping drift validation.")
                click.echo()
            else:
                try:
                    # Build DACPAC
                    result = subprocess.run(
                        ['dotnet', 'build', str(project_path), '-c', 'Debug', '--nologo'],
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    if result.returncode != 0:
                        click.secho("⚠ Project build failed. Skipping drift validation.", fg="yellow")
                        click.echo()
                    else:
                        project_dir = project_path.parent
                        dacpac_name = project_path.stem + '.dacpac'
                        project_dacpac = project_dir / 'bin' / 'Debug' / dacpac_name

                        # Extract database DACPAC
                        with tempfile.NamedTemporaryFile(suffix='.dacpac', delete=False) as temp_file:
                            database_dacpac = Path(temp_file.name)

                        try:
                            success, error = extract_database_dacpac(
                                server=server,
                                database=database,
                                user=user,
                                password=password,
                                output_path=database_dacpac
                            )

                            if not success:
                                click.secho(f"⚠ Could not extract database schema: {error}", fg="yellow")
                                click.echo("  Skipping drift validation.")
                                click.echo()
                            else:
                                # Compare DACPACs
                                drift_data = compare_database_to_project(
                                    project_dacpac=project_dacpac,
                                    database_dacpac=database_dacpac
                                )

                                if 'error' in drift_data:
                                    click.secho(f"⚠ Drift comparison failed: {drift_data['error']}", fg="yellow")
                                    click.echo("  Skipping drift validation.")
                                    click.echo()
                                elif not drift_data.get('has_drift', False):
                                    click.secho("✓ No drift detected", fg="green")
                                    click.echo()
                                else:
                                    # Categorize drift
                                    changes = drift_data.get('changes', [])
                                    categorized = categorize_drift(changes, ToleranceLevel.NORMAL)

                                    unacceptable = [c for c in categorized if not c['acceptable']]
                                    acceptable = [c for c in categorized if c['acceptable']]

                                    if len(unacceptable) > 0:
                                        click.secho("✗ Schema drift detected!", fg="red", err=True)
                                        click.echo()
                                        click.echo(f"  Found {len(unacceptable)} unacceptable drift(s):")

                                        for drift in unacceptable[:5]:
                                            obj_type = drift.get('object_type', 'OBJECT')
                                            obj_name = drift.get('object_name', 'unknown')
                                            drift_type = drift.get('type', 'CHANGE')
                                            click.echo(f"    • {drift_type} {obj_type} [{obj_name}]")

                                        if len(unacceptable) > 5:
                                            click.echo(f"    ... and {len(unacceptable) - 5} more")

                                        click.echo()
                                        click.secho("  Run 'dbctl drift' to see full report", fg="cyan")
                                        click.secho("  Run 'dbctl drift --fix' to generate repair migration", fg="cyan")
                                        click.echo()

                                        if not force:
                                            click.secho("  Use --force to migrate anyway (not recommended)", fg="yellow")
                                            click.echo()
                                            click.secho("Migration aborted due to drift.", fg="red", bold=True)
                                            raise click.Abort()
                                        else:
                                            click.secho("  WARNING: Proceeding with migration despite drift (--force)", fg="yellow", bold=True)
                                            click.echo()
                                    else:
                                        if len(acceptable) > 0:
                                            click.secho(f"✓ Only acceptable drift detected ({len(acceptable)} change(s))", fg="green")
                                        else:
                                            click.secho("✓ No drift detected", fg="green")
                                        click.echo()
                        finally:
                            # Clean up temp DACPAC
                            if database_dacpac.exists():
                                database_dacpac.unlink()

                except Exception as e:
                    click.secho(f"⚠ Drift validation error: {e}", fg="yellow")
                    click.echo("  Continuing with migration...")
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

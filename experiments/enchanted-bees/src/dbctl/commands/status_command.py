"""
Status command - Show database and migration status
"""

import click
import subprocess
import os
import pyodbc
from pathlib import Path


def status(ctx):
    """Show database and migration status"""
    click.secho("Database Status", fg="cyan", bold=True)
    click.echo()

    # Database connection info
    db_server = os.getenv('DB_SERVER', 'sqlserver')
    db_port = os.getenv('DB_PORT', '1433')
    db_name = os.getenv('DB_NAME', 'EnchantedBeesDB')
    db_user = os.getenv('DB_USER', 'sa')
    db_password = os.getenv('DB_PASSWORD', '')

    click.secho("Connection:", fg="yellow")
    click.echo(f"  Server: {db_server}:{db_port}")
    click.echo(f"  Database: {db_name}")
    click.echo(f"  User: {db_user}")
    click.echo()

    # Test database connectivity
    if not db_password:
        click.secho("⚠ DB_PASSWORD not set, cannot test connectivity", fg="yellow")
    else:
        click.secho("Testing connectivity...", fg="yellow")
        try:
            target_server = f"{db_server},{db_port}" if db_port else db_server
            result = subprocess.run(
                [
                    'sqlcmd',
                    '-S', target_server,
                    '-U', db_user,
                    '-P', db_password,
                    '-d', 'master',
                    '-Q', 'SELECT @@VERSION',
                    '-C'  # Trust server certificate
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            click.secho("✓ Database server is reachable", fg="green")

            # Check if our database exists
            result = subprocess.run(
                [
                    'sqlcmd',
                    '-S', target_server,
                    '-U', db_user,
                    '-P', db_password,
                    '-d', 'master',
                    '-Q', f"SELECT name FROM sys.databases WHERE name = '{db_name}'",
                    '-h', '-1',  # No headers
                    '-C'
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            if db_name in result.stdout:
                click.secho(f"✓ Database '{db_name}' exists", fg="green")
            else:
                click.secho(f"⚠ Database '{db_name}' does not exist", fg="yellow")

        except subprocess.TimeoutExpired:
            click.secho("✗ Connection timeout", fg="red", err=True)
        except subprocess.CalledProcessError as e:
            click.secho("✗ Cannot connect to database", fg="red", err=True)
            if e.stderr:
                click.echo(f"  Error: {e.stderr.strip()}", err=True)
        except Exception as e:
            click.secho(f"✗ Error: {e}", fg="red", err=True)

    click.echo()
    click.secho("Migrations:", fg="yellow")

    # Try to show migration status
    try:
        from ..migration_tracker import get_connection_string, get_applied_migrations
        from ..migration_executor import discover_migrations, get_pending_migrations

        workspace_root = ctx.obj.get('WORKSPACE_ROOT', Path('/workspace'))
        migrations_dir = workspace_root / 'migrations' / db_name

        # Connect to database
        conn_string = get_connection_string(db_server, db_name, db_user, db_password)
        conn = pyodbc.connect(conn_string, autocommit=True)

        try:
            # Get migration counts
            all_migrations = discover_migrations(migrations_dir)
            applied_migrations = get_applied_migrations(conn)
            pending_migrations = get_pending_migrations(migrations_dir, conn)

            click.echo(f"  Total migrations: {len(all_migrations)}")
            click.echo(f"  Applied: {len(applied_migrations)}")
            click.echo(f"  Pending: {len(pending_migrations)}")

            if len(pending_migrations) > 0:
                click.echo()
                click.secho("  Next migrations to apply:", fg="yellow")
                for mig in pending_migrations[:5]:  # Show first 5
                    click.echo(f"    • {mig['migration_id']}")
                if len(pending_migrations) > 5:
                    click.echo(f"    ... and {len(pending_migrations) - 5} more")

                click.echo()
                click.secho("  Run 'dbctl migrate' to apply pending migrations", fg="cyan")
            else:
                click.secho("  ✓ Database is up to date!", fg="green")

        finally:
            conn.close()

    except Exception as e:
        click.echo(f"  Could not check migration status: {e}")

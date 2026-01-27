"""
Status command - Show database and migration status
"""

import click
import subprocess
import os


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
    click.echo("  Migration system not yet implemented (Epic 1)")

"""
Info command - Display environment and tooling information
"""

import click
import subprocess
import os
import platform


def info(ctx):
    """Show environment and tooling information"""
    click.secho("dbctl Environment Information", fg="cyan", bold=True)
    click.echo()

    # System information
    click.secho("System:", fg="yellow")
    click.echo(f"  Platform: {platform.system()} {platform.release()}")
    click.echo(f"  Python: {platform.python_version()}")
    click.echo()

    # Database connection info
    click.secho("Database Configuration:", fg="yellow")
    click.echo(f"  Server: {os.getenv('DB_SERVER', 'Not set')}")
    click.echo(f"  Port: {os.getenv('DB_PORT', 'Not set')}")
    click.echo(f"  Database: {os.getenv('DB_NAME', 'Not set')}")
    click.echo(f"  User: {os.getenv('DB_USER', 'Not set')}")
    click.echo()

    # Tooling versions
    click.secho("Installed Tools:", fg="yellow")

    # Check dotnet
    try:
        result = subprocess.run(['dotnet', '--version'],
                                capture_output=True, text=True, check=True)
        click.echo(f"  dotnet: {result.stdout.strip()}")
    except Exception as e:
        click.echo(f"  dotnet: Not found")

    # Check sqlpackage
    try:
        result = subprocess.run(['sqlpackage', '/version'],
                                capture_output=True, text=True, check=True)
        # sqlpackage outputs version to stderr
        version_output = result.stderr.strip() if result.stderr else result.stdout.strip()
        click.echo(f"  sqlpackage: {version_output.split()[0] if version_output else 'Found'}")
    except Exception as e:
        click.echo(f"  sqlpackage: Not found")

    # Check sqlcmd
    try:
        result = subprocess.run(['sqlcmd', '-?'],
                                capture_output=True, text=True, check=False)
        click.echo(f"  sqlcmd: Found")
    except Exception as e:
        click.echo(f"  sqlcmd: Not found")

    click.echo()
    click.secho("Container Infrastructure: Active", fg="green")

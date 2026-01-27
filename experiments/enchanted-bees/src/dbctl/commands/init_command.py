"""
Init command - Initialize/publish database to SQL Server
"""

import click
import subprocess
from pathlib import Path


def init(ctx, project: str, configuration: str, server: str, database: str, user: str, password: str):
    """
    Initialize and publish database to SQL Server

    This command:
    1. Builds the SQL project to generate DACPAC
    2. Publishes the DACPAC to the target SQL Server
    3. Creates the database if it doesn't exist
    """
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    project_path = workspace_root / project

    if not project_path.exists():
        click.secho(f"Error: Project file not found: {project_path}", fg="red", err=True)
        raise click.Abort()

    project_dir = project_path.parent
    project_name = project_path.stem
    dacpac_path = project_dir / 'bin' / configuration / f'{project_name}.dacpac'

    click.secho("=" * 60, fg="cyan")
    click.secho("  Database Initialization", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    # Step 1: Build the SQL project
    click.secho("Step 1: Building SQL project...", fg="cyan", bold=True)
    click.echo(f"  Project: {project}")
    click.echo(f"  Configuration: {configuration}")
    click.echo()

    if not build_project(project_path, configuration):
        click.secho("✗ Build failed. Cannot initialize database.", fg="red", err=True)
        raise click.Abort()

    if not dacpac_path.exists():
        click.secho(f"✗ DACPAC not found at: {dacpac_path}", fg="red", err=True)
        raise click.Abort()

    click.secho(f"✓ Build successful", fg="green")
    click.echo(f"  DACPAC: {dacpac_path.relative_to(workspace_root)}")
    click.echo()

    # Step 2: Publish to SQL Server
    click.secho("Step 2: Publishing to SQL Server...", fg="cyan", bold=True)
    click.echo(f"  Server: {server}")
    click.echo(f"  Database: {database}")
    click.echo(f"  User: {user}")
    click.echo()

    try:
        publish_dacpac(
            dacpac_path=dacpac_path,
            server=server,
            database=database,
            user=user,
            password=password
        )
    except Exception as e:
        click.secho(f"✗ Publish failed: {e}", fg="red", err=True)
        raise click.Abort()

    click.secho("✓ Database published successfully!", fg="green")
    click.echo()

    # Summary
    click.secho("=" * 60, fg="cyan")
    click.secho("  Initialization Complete!", fg="green", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo("Your database is ready:")
    click.echo(f"  Server:   {server}")
    click.echo(f"  Database: {database}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Verify schema: dbctl status")
    click.echo("  2. Generate migrations for future changes: dbctl generate")
    click.echo()


def build_project(project_path: Path, configuration: str) -> bool:
    """
    Build SQL project and return success status

    Returns:
        True if build successful, False otherwise
    """
    try:
        result = subprocess.run(
            ['dotnet', 'build', str(project_path), '-c', configuration, '--nologo'],
            capture_output=True,
            text=True,
            check=False
        )

        # Check for errors in output
        if result.returncode != 0:
            click.echo(result.stdout)
            click.echo(result.stderr, err=True)
            return False

        return True

    except Exception as e:
        click.secho(f"Build error: {e}", fg="red", err=True)
        return False


def publish_dacpac(
    dacpac_path: Path,
    server: str,
    database: str,
    user: str,
    password: str
) -> None:
    """
    Publish DACPAC to SQL Server using sqlpackage

    Args:
        dacpac_path: Path to the DACPAC file
        server: SQL Server hostname
        database: Target database name
        user: SQL Server username
        password: SQL Server password

    Raises:
        RuntimeError: If publish fails
    """
    # Build connection string
    connection_string = (
        f"Server={server};Database={database};User Id={user};Password={password};"
        "TrustServerCertificate=True;Encrypt=True;"
    )

    # Build sqlpackage command
    cmd = [
        'sqlpackage',
        '/Action:Publish',
        f'/SourceFile:{dacpac_path}',
        f'/TargetConnectionString:{connection_string}',
        '/p:CreateNewDatabase=True',  # Create database if it doesn't exist
        '/p:IncludeCompositeObjects=True',
        '/p:BlockOnPossibleDataLoss=False',  # Allow schema changes that might lose data
        '/p:DropObjectsNotInSource=False',  # Don't drop objects not in source (safer)
    ]

    try:
        click.echo("  Executing sqlpackage publish...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        # Show output
        if result.stdout:
            # Parse output for key messages
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Microsoft'):
                    if 'Successfully' in line or 'Creating' in line or 'Adding' in line:
                        click.echo(f"  {line}")

        # Check for errors
        if result.returncode != 0:
            click.echo(result.stdout)
            click.echo(result.stderr, err=True)
            raise RuntimeError(f"sqlpackage failed with exit code {result.returncode}")

        # Check stderr for warnings (sqlpackage sometimes puts info in stderr)
        if result.stderr:
            stderr_lower = result.stderr.lower()
            if 'error' in stderr_lower or 'failed' in stderr_lower:
                raise RuntimeError(f"Publish error: {result.stderr}")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to publish DACPAC: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during publish: {e}")

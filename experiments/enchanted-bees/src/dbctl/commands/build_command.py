"""
Build command - Build SQL project and generate DACPAC
"""

import click
import subprocess
from pathlib import Path


def build(ctx, project, configuration):
    """Build SQL project and generate DACPAC"""
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    project_path = workspace_root / project

    if not project_path.exists():
        click.secho(f"Error: Project file not found: {project_path}", fg="red", err=True)
        raise click.Abort()

    click.secho(f"Building SQL project: {project}", fg="cyan")
    click.echo(f"  Configuration: {configuration}")
    click.echo()

    # Build the project using dotnet
    try:
        result = subprocess.run(
            ['dotnet', 'build', str(project_path), '-c', configuration],
            capture_output=True,
            text=True,
            check=True
        )

        # Show output
        if result.stdout:
            click.echo(result.stdout)

        # Determine DACPAC path
        project_dir = project_path.parent
        dacpac_name = project_path.stem + '.dacpac'
        dacpac_path = project_dir / 'bin' / configuration / dacpac_name

        if dacpac_path.exists():
            click.secho(f"✓ Build successful!", fg="green")
            click.echo(f"  DACPAC: {dacpac_path.relative_to(workspace_root)}")
        else:
            click.secho(f"⚠ Build completed but DACPAC not found at expected location:", fg="yellow")
            click.echo(f"  Expected: {dacpac_path.relative_to(workspace_root)}")

    except subprocess.CalledProcessError as e:
        click.secho("✗ Build failed!", fg="red", err=True)
        click.echo(e.stdout, err=True)
        click.echo(e.stderr, err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        raise click.Abort()

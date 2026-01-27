"""
Generate command - Generate migration scripts from SQL project changes
"""

import click
import subprocess
from pathlib import Path
from typing import Optional

from ..dacpac_utils import (
    get_dacpac_hash,
    copy_baseline_dacpac,
    get_latest_baseline,
    compare_dacpacs,
    parse_schema_changes
)
from ..migration_generator import (
    generate_timestamp,
    generate_description,
    generate_up_migration,
    generate_down_migration,
    save_migration_files
)


def generate(ctx, project: str, configuration: str, message: Optional[str], init: bool):
    """
    Generate migration scripts from SQL project changes

    This command:
    1. Builds the SQL project to generate current DACPAC
    2. Compares against baseline DACPAC (or creates initial baseline)
    3. Detects schema changes
    4. Generates timestamped migration files (UP and DOWN)
    5. Updates baseline reference
    """
    workspace_root = ctx.obj['WORKSPACE_ROOT']
    project_path = workspace_root / project

    if not project_path.exists():
        click.secho(f"Error: Project file not found: {project_path}", fg="red", err=True)
        raise click.Abort()

    # Paths
    project_dir = project_path.parent
    project_name = project_path.stem
    migrations_dir = workspace_root / 'migrations'
    baseline_dir = workspace_root / '.dbctl' / 'baselines'
    dacpac_path = project_dir / 'bin' / configuration / f'{project_name}.dacpac'

    click.secho("=" * 60, fg="cyan")
    click.secho("  Migration Generation", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    # Step 1: Build the SQL project
    click.secho("Step 1: Building SQL project...", fg="cyan", bold=True)
    if not build_project(project_path, configuration):
        click.secho("✗ Build failed. Cannot generate migration.", fg="red", err=True)
        raise click.Abort()

    if not dacpac_path.exists():
        click.secho(f"✗ DACPAC not found at: {dacpac_path}", fg="red", err=True)
        raise click.Abort()

    click.secho(f"✓ Build successful: {dacpac_path.relative_to(workspace_root)}", fg="green")
    click.echo()

    # Step 2: Get or create baseline
    click.secho("Step 2: Checking baseline...", fg="cyan", bold=True)

    baseline_dacpac = get_latest_baseline(baseline_dir, project_name)

    if init or baseline_dacpac is None:
        # Create initial baseline
        click.echo("  No baseline found. Creating initial baseline...")
        baseline_dacpac = copy_baseline_dacpac(dacpac_path, baseline_dir)
        click.secho(f"✓ Initial baseline created: {baseline_dacpac.name}", fg="green")
        click.echo()
        click.secho("Migration generation complete. Use --init flag to create future migrations.", fg="yellow")
        return

    click.echo(f"  Baseline: {baseline_dacpac.name}")
    click.echo()

    # Step 3: Compare DACPACs
    click.secho("Step 3: Comparing schemas...", fg="cyan", bold=True)

    try:
        comparison = compare_dacpacs(dacpac_path, baseline_dacpac)
    except Exception as e:
        click.secho(f"✗ Comparison failed: {e}", fg="red", err=True)
        raise click.Abort()

    if not comparison['has_changes']:
        click.secho("✓ No schema changes detected.", fg="green")
        click.echo()
        click.echo("The current schema matches the baseline. No migration needed.")
        return

    click.secho("✓ Schema changes detected!", fg="green")
    click.echo()

    # Step 4: Parse changes
    click.secho("Step 4: Analyzing changes...", fg="cyan", bold=True)

    changes = parse_schema_changes(comparison)

    if changes:
        click.echo(f"  Found {len(changes)} schema change(s):")
        for change in changes:
            operation = change.get('type', 'UNKNOWN')
            obj_type = change.get('object_type', '')
            obj_name = change.get('object_name', '')
            click.echo(f"    - {operation} {obj_type} [{obj_name}]")
    else:
        click.echo("  Changes detected but could not parse details.")

    click.echo()

    # Step 5: Generate migration description
    timestamp = generate_timestamp()

    if message:
        description = message.lower().replace(' ', '_').replace('-', '_')
        # Sanitize
        description = ''.join(c for c in description if c.isalnum() or c == '_')
    else:
        description = generate_description(changes)

    click.secho("Step 5: Generating migration files...", fg="cyan", bold=True)
    click.echo(f"  Migration: {timestamp}_{description}")
    click.echo()

    # Step 6: Generate UP migration
    baseline_hash = get_dacpac_hash(baseline_dacpac)[:12]

    up_script = generate_up_migration(
        changes=changes,
        script=comparison['script'],
        timestamp=timestamp,
        description=description,
        baseline_hash=baseline_hash
    )

    # Step 7: Generate DOWN migration
    down_script = generate_down_migration(
        changes=changes,
        timestamp=timestamp,
        description=description
    )

    # Step 8: Save migration files
    up_path, down_path = save_migration_files(
        migrations_dir=migrations_dir,
        timestamp=timestamp,
        description=description,
        up_script=up_script,
        down_script=down_script
    )

    click.secho("✓ Migration files created:", fg="green")
    click.echo(f"  UP:   {up_path.relative_to(workspace_root)}")
    if down_path:
        click.echo(f"  DOWN: {down_path.relative_to(workspace_root)}")
    click.echo()

    # Step 9: Update baseline
    click.secho("Step 6: Updating baseline...", fg="cyan", bold=True)
    new_baseline = copy_baseline_dacpac(dacpac_path, baseline_dir)
    click.secho(f"✓ Baseline updated: {new_baseline.name}", fg="green")
    click.echo()

    # Summary
    click.secho("=" * 60, fg="cyan")
    click.secho("  Migration Generation Complete!", fg="green", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo(f"Next steps:")
    click.echo(f"  1. Review migration: {up_path.relative_to(workspace_root)}")
    click.echo(f"  2. Apply migration:  dbctl migrate (coming soon)")
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

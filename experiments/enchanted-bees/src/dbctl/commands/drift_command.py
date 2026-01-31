"""
Drift command - Detect schema drift between database and SQL project
"""

import click
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..drift_detector import (
    extract_database_dacpac,
    compare_database_to_project,
    categorize_drift,
    generate_drift_report,
    ToleranceLevel
)


def drift(
    ctx,
    server: str,
    database: str,
    user: str,
    password: str,
    project: str,
    configuration: str,
    baseline: Optional[str],
    output: str,
    report_file: Optional[str],
    dry_run: bool,
    fix: bool,
    tolerance: str,
    exit_code: bool
):
    """
    Detect schema drift between database and SQL project

    This command compares the actual database schema against the expected
    state defined in the SQL project, identifying any differences (drift).
    """
    click.echo()
    click.secho("=" * 60, fg="cyan")
    click.secho("  Drift Detection", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    workspace_root = ctx.obj.get('WORKSPACE_ROOT', Path('/workspace'))
    has_drift = False
    has_unacceptable_drift = False

    try:
        # Parse tolerance level
        try:
            tolerance_level = ToleranceLevel[tolerance.upper()]
        except KeyError:
            click.secho(f"✗ Invalid tolerance level: {tolerance}", fg="red", err=True)
            click.secho(f"Valid options: strict, normal, permissive", fg="yellow")
            raise click.Abort()

        # Step 1: Build project DACPAC (expected state)
        click.secho("Step 1: Building SQL project...", fg="cyan", bold=True)

        if baseline:
            # Use specific baseline DACPAC
            project_dacpac = Path(baseline)
            if not project_dacpac.exists():
                click.secho(f"✗ Baseline DACPAC not found: {baseline}", fg="red", err=True)
                raise click.Abort()
            click.secho(f"✓ Using baseline: {project_dacpac}", fg="green")
        else:
            # Build from SQL project
            project_path = workspace_root / project

            if not project_path.exists():
                click.secho(f"✗ Project file not found: {project}", fg="red", err=True)
                raise click.Abort()

            # Build DACPAC using dotnet build
            try:
                result = subprocess.run(
                    ['dotnet', 'build', str(project_path), '-c', configuration, '--nologo'],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode != 0:
                    click.secho("✗ Build failed", fg="red", err=True)
                    click.echo(result.stdout)
                    click.echo(result.stderr, err=True)
                    raise click.Abort()

            except Exception as e:
                click.secho(f"✗ Build error: {e}", fg="red", err=True)
                raise click.Abort()

            # Determine DACPAC path
            project_dir = project_path.parent
            dacpac_name = project_path.stem + '.dacpac'
            project_dacpac = project_dir / 'bin' / configuration / dacpac_name

            if not project_dacpac.exists():
                click.secho(f"✗ DACPAC not found at: {project_dacpac}", fg="red", err=True)
                raise click.Abort()

            click.secho(f"✓ Build successful: {project_dacpac}", fg="green")

        click.echo()

        # Step 2: Connect to database
        click.secho("Step 2: Connecting to database...", fg="cyan", bold=True)
        click.echo(f"  Server: {server}")
        click.echo(f"  Database: {database}")
        click.echo(f"  User: {user}")

        if dry_run:
            click.secho("✓ Dry-run mode: skipping connection", fg="yellow")
            click.echo()
            click.secho("Dry-run complete. Would check drift against:", fg="cyan")
            click.echo(f"  Project: {project_dacpac}")
            click.echo(f"  Database: {server}/{database}")
            return

        # Test connectivity
        try:
            result = subprocess.run(
                [
                    'sqlcmd',
                    '-S', server,
                    '-U', user,
                    '-P', password,
                    '-d', database,
                    '-Q', 'SELECT 1',
                    '-C'  # Trust server certificate
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            click.secho("✓ Connected successfully", fg="green")
        except subprocess.TimeoutExpired:
            click.secho("✗ Connection timeout", fg="red", err=True)
            raise click.Abort()
        except subprocess.CalledProcessError as e:
            click.secho("✗ Cannot connect to database", fg="red", err=True)
            if e.stderr:
                click.echo(f"  Error: {e.stderr.strip()}", err=True)
            raise click.Abort()

        click.echo()

        # Step 3: Extract database DACPAC (actual state)
        click.secho("Step 3: Extracting database schema...", fg="cyan", bold=True)

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
                click.secho("✗ Extraction failed", fg="red", err=True)
                if error:
                    click.echo(f"  Error: {error}", err=True)
                raise click.Abort()

            click.secho(f"✓ Extracted: {database_dacpac}", fg="green")
            click.echo()

            # Step 4: Compare schemas
            click.secho("Step 4: Comparing schemas...", fg="cyan", bold=True)

            drift_data = compare_database_to_project(
                project_dacpac=project_dacpac,
                database_dacpac=database_dacpac
            )

            if 'error' in drift_data:
                click.secho("✗ Comparison failed", fg="red", err=True)
                click.echo(f"  Error: {drift_data['error']}", err=True)
                raise click.Abort()

            click.secho("✓ Comparison complete", fg="green")
            click.echo()

            # Step 5: Analyze drift
            click.secho("Step 5: Analyzing drift...", fg="cyan", bold=True)

            has_drift = drift_data.get('has_drift', False)

            if not has_drift:
                click.secho("✓ No drift detected", fg="green")
                click.echo()
                click.secho("=" * 60, fg="cyan")
                click.echo()
                click.secho("✓ Database schema matches SQL project perfectly!", fg="green", bold=True)
                click.echo()
                click.echo("Database is in sync with expected state.")
                click.echo()

                # Save report if requested
                if report_file:
                    environment = {
                        "server": server,
                        "database": database
                    }
                    report_content = generate_drift_report(
                        drift_data=drift_data,
                        categorized_changes=[],
                        tolerance=tolerance,
                        environment=environment,
                        output_format=output
                    )
                    Path(report_file).write_text(report_content, encoding='utf-8')
                    click.secho(f"✓ Report saved to: {report_file}", fg="green")

                return  # Exit successfully

            # Categorize drift
            changes = drift_data.get('changes', [])
            categorized_changes = categorize_drift(changes, tolerance_level)

            acceptable_count = sum(1 for c in categorized_changes if c['acceptable'])
            unacceptable_count = len(categorized_changes) - acceptable_count

            click.echo(f"  Drift detected: {len(categorized_changes)} change(s)")
            click.echo(f"  Acceptable drift: {acceptable_count} change(s)")
            click.echo(f"  Unacceptable drift: {unacceptable_count} change(s)")
            click.echo()

            has_unacceptable_drift = unacceptable_count > 0

            # Step 6: Generate report
            click.secho("=" * 60, fg="cyan")
            click.secho("  Drift Report", fg="cyan", bold=True)
            click.secho("=" * 60, fg="cyan")
            click.echo()

            environment = {
                "server": server,
                "database": database
            }

            report_content = generate_drift_report(
                drift_data=drift_data,
                categorized_changes=categorized_changes,
                tolerance=tolerance,
                environment=environment,
                output_format=output
            )

            if output == "json" or output == "xml":
                # Print JSON/XML to stdout
                click.echo(report_content)
            else:
                # Print table format
                click.echo(report_content)

            click.echo()
            click.secho("=" * 60, fg="cyan")
            click.echo()

            # Save report if requested
            if report_file:
                Path(report_file).write_text(report_content, encoding='utf-8')
                click.secho(f"✓ Report saved to: {report_file}", fg="green")
                click.echo()

            # Show next steps
            if has_unacceptable_drift:
                click.echo("Next steps:")
                click.echo("  1. Review drift: dbctl drift --output json > drift.json")
                if fix:
                    click.echo("  2. Repair migration will be generated below...")
                else:
                    click.echo("  2. Generate repair: dbctl drift --fix")
                click.echo()

            # Step 7: Generate repair migration (if requested)
            if fix:
                from ..drift_detector import generate_repair_migration

                click.secho("Step 6: Generating repair migration...", fg="cyan", bold=True)

                migrations_dir = workspace_root / 'migrations' / database

                try:
                    up_path, down_path = generate_repair_migration(
                        drift_data=drift_data,
                        migrations_dir=migrations_dir,
                        database=database
                    )

                    # Get migration name from path
                    migration_name = up_path.stem

                    click.echo(f"  Migration: {migration_name}")
                    click.echo()
                    click.secho("✓ Migration files created:", fg="green")
                    click.echo(f"  UP:   {up_path}")
                    click.echo(f"  DOWN: {down_path}")
                    click.echo()

                    # Check if there are DROP operations
                    script_content = drift_data.get('script', '')
                    has_drops = 'DROP ' in script_content.upper()

                    if has_drops:
                        click.secho("=" * 60, fg="yellow")
                        click.secho("  Repair Migration Generated", fg="yellow", bold=True)
                        click.secho("=" * 60, fg="yellow")
                        click.echo()
                        click.secho("WARNINGS:", fg="yellow", bold=True)
                        click.secho("  ⚠ This migration will DROP objects not in SQL project", fg="yellow")
                        click.secho("  ⚠ MANUAL REVIEW REQUIRED before applying", fg="yellow")
                        click.echo()

                        # Show which objects will be dropped
                        extra_objects = [c for c in categorized_changes
                                       if c.get('drift_type') == 'extra']
                        if extra_objects:
                            click.echo("Affected objects:")
                            for obj in extra_objects:
                                obj_type = obj.get('object_type', 'OBJECT')
                                obj_name = obj.get('object_name', 'unknown')
                                click.echo(f"  - {obj_type} [{obj_name}] (WILL BE DROPPED)")
                            click.echo()

                    click.echo("Next steps:")
                    click.echo(f"  1. Review: {up_path}")
                    if has_drops:
                        click.echo("  2. Edit if needed (uncomment DROP statements)")
                    click.echo("  3. Apply: dbctl migrate")
                    click.echo()

                except Exception as e:
                    click.secho("✗ Failed to generate repair migration", fg="red", err=True)
                    click.echo(f"  Error: {str(e)}", err=True)

        finally:
            # Clean up temp database DACPAC
            if database_dacpac.exists():
                database_dacpac.unlink()

    except click.Abort:
        # User-friendly abort
        if exit_code:
            raise SystemExit(2)  # Error exit code
        else:
            raise

    except Exception as e:
        click.secho(f"✗ Unexpected error: {str(e)}", fg="red", err=True)
        if exit_code:
            raise SystemExit(2)  # Error exit code
        else:
            raise click.Abort()

    # Exit with appropriate code
    if exit_code:
        if has_unacceptable_drift:
            raise SystemExit(1)  # Drift detected
        else:
            raise SystemExit(0)  # No drift or only acceptable drift

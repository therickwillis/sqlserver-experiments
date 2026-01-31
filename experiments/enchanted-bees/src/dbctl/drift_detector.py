"""
Drift detector - Detect schema drift between database and SQL project

This module provides functionality to detect schema differences between
a live database environment and the expected state defined in the SQL project.
"""

import subprocess
import tempfile
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

from .dacpac_utils import parse_schema_changes


class DriftType(Enum):
    """Types of drift that can be detected"""
    MISSING_OBJECT = "missing"   # Object exists in project, not in database
    EXTRA_OBJECT = "extra"       # Object exists in database, not in project
    MODIFIED_OBJECT = "modified" # Object definition differs between project and database
    ACCEPTABLE = "acceptable"    # Whitelisted drift (e.g., performance indexes)


class ToleranceLevel(Enum):
    """Drift tolerance levels"""
    STRICT = "strict"           # Any difference is drift
    NORMAL = "normal"           # Allow performance indexes/statistics
    PERMISSIVE = "permissive"   # Allow performance objects + extended properties


def extract_database_dacpac(
    server: str,
    database: str,
    user: str,
    password: str,
    output_path: Path
) -> Tuple[bool, Optional[str]]:
    """
    Extract DACPAC from live database using sqlpackage /Action:Extract

    Args:
        server: SQL Server hostname
        database: Database name
        user: Username for authentication
        password: Password for authentication
        output_path: Path where DACPAC should be saved

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Build connection string with TrustServerCertificate for self-signed certs
        connection_string = (
            f"Server={server};Database={database};User Id={user};Password={password};"
            "TrustServerCertificate=True;Encrypt=True;"
        )

        # Build sqlpackage Extract command
        cmd = [
            'sqlpackage',
            '/Action:Extract',
            f'/SourceConnectionString:{connection_string}',
            f'/TargetFile:{output_path}',
            '/p:ExtractAllTableData=False',  # Schema only, no data
            '/p:VerifyExtraction=True'      # Validate extraction
        ]

        # Execute sqlpackage
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            return False, f"DACPAC extraction failed: {error_msg}"

        # Verify output file was created
        if not output_path.exists():
            return False, f"DACPAC file not created at {output_path}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "DACPAC extraction timed out after 5 minutes"
    except Exception as e:
        return False, f"Unexpected error during extraction: {str(e)}"


def compare_database_to_project(
    project_dacpac: Path,
    database_dacpac: Path
) -> Dict:
    """
    Compare project (expected) against database (actual) state

    This reuses the Epic 1 DACPAC comparison pattern to detect schema differences.

    Args:
        project_dacpac: Path to DACPAC built from SQL project (expected state)
        database_dacpac: Path to DACPAC extracted from database (actual state)

    Returns:
        Dict with:
        - has_drift: bool
        - drift_count: int
        - changes: List[Dict] (parsed schema changes)
        - script: str (SQL script to fix drift)
        - report_xml: str (full XML report from sqlpackage)
    """
    try:
        # Create temp files for comparison outputs
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as report_file:
            report_path = Path(report_file.name)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as script_file:
            script_path = Path(script_file.name)

        try:
            # Generate deployment report (comparison)
            report_cmd = [
                'sqlpackage',
                '/Action:DeployReport',
                f'/SourceFile:{project_dacpac}',  # Expected (project)
                f'/TargetFile:{database_dacpac}',  # Actual (database)
                f'/OutputPath:{report_path}',
                '/TargetDatabaseName:TempDB',
                '/p:CommentOutSetVarDeclarations=True'
            ]

            report_result = subprocess.run(
                report_cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=120
            )

            if report_result.returncode != 0:
                return {
                    'has_drift': False,
                    'drift_count': 0,
                    'changes': [],
                    'script': '',
                    'report_xml': '',
                    'error': f"Comparison failed: {report_result.stderr}"
                }

            # Read report XML
            report_xml = ''
            if report_path.exists():
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_xml = f.read()

            # Check for operations (changes)
            operations = re.findall(r'<Operation Name="([^"]+)"', report_xml)
            has_drift = len(operations) > 0

            if not has_drift:
                return {
                    'has_drift': False,
                    'drift_count': 0,
                    'changes': [],
                    'script': '',
                    'report_xml': report_xml
                }

            # Generate script to fix drift
            script_cmd = [
                'sqlpackage',
                '/Action:Script',
                f'/SourceFile:{project_dacpac}',  # Expected (project)
                f'/TargetFile:{database_dacpac}',  # Actual (database)
                f'/OutputPath:{script_path}',
                '/p:CommentOutSetVarDeclarations=True',
                '/p:IncludeTransactionalScripts=True',
                '/TargetDatabaseName:TempDB'
            ]

            script_result = subprocess.run(
                script_cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=120
            )

            # Read script
            script = ''
            if script_path.exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    script = f.read()

            # Build comparison result dict for parsing
            comparison_result = {
                'script': script,
                'report_xml': report_xml
            }

            # Parse schema changes from script
            changes = parse_schema_changes(comparison_result)

            return {
                'has_drift': True,
                'drift_count': len(changes),
                'changes': changes,
                'script': script,
                'report_xml': report_xml
            }

        finally:
            # Clean up temp files
            if report_path.exists():
                report_path.unlink()
            if script_path.exists():
                script_path.unlink()

    except subprocess.TimeoutExpired:
        return {
            'has_drift': False,
            'drift_count': 0,
            'changes': [],
            'script': '',
            'report_xml': '',
            'error': 'Comparison timed out'
        }
    except Exception as e:
        return {
            'has_drift': False,
            'drift_count': 0,
            'changes': [],
            'script': '',
            'report_xml': '',
            'error': f'Unexpected error: {str(e)}'
        }


def is_acceptable_drift(change: Dict, tolerance: ToleranceLevel) -> bool:
    """
    Determine if a change is acceptable drift based on tolerance level

    Args:
        change: Dict with keys: type, object_type, object_name, sql
        tolerance: ToleranceLevel enum value

    Returns:
        bool: True if drift is acceptable, False otherwise
    """
    if tolerance == ToleranceLevel.STRICT:
        # Strict tolerance: no drift is acceptable
        return False

    operation = change.get('type', '').upper()
    object_type = change.get('object_type', '').upper()
    object_name = change.get('object_name', '')

    # Normal tolerance: Allow performance optimizations
    if tolerance == ToleranceLevel.NORMAL or tolerance == ToleranceLevel.PERMISSIVE:
        # Auto-generated statistics
        if object_type == 'STATISTICS':
            return True

        # Auto-generated indexes (SQL Server creates these with _WA_Sys prefix)
        if object_type == 'INDEX' and '_WA_Sys_' in object_name:
            return True

        # Non-clustered performance indexes (typically have IX_ or IDX_ prefix)
        if object_type == 'INDEX' and (
            object_name.startswith('IX_') or
            object_name.startswith('IDX_') or
            'Performance' in object_name or
            'Perf' in object_name
        ):
            # Only accept if it's a CREATE operation (adding performance index)
            # Don't accept ALTERs or DROPs of indexes
            if operation == 'CREATE':
                return True

        # Query store objects
        if 'query_store' in object_name.lower():
            return True

    # Permissive tolerance: Also allow extended properties and descriptions
    if tolerance == ToleranceLevel.PERMISSIVE:
        if object_type in ['EXTENDED_PROPERTY', 'DESCRIPTION']:
            return True

    return False


def categorize_drift(
    changes: List[Dict],
    tolerance: ToleranceLevel
) -> List[Dict]:
    """
    Categorize changes by drift type based on tolerance level

    Args:
        changes: List of schema changes from parse_schema_changes()
        tolerance: ToleranceLevel enum value

    Returns:
        List of dicts with added fields:
        - drift_type: DriftType enum value
        - acceptable: bool
    """
    categorized = []

    for change in changes:
        operation = change.get('type', '').upper()
        object_type = change.get('object_type', '').upper()

        # Determine drift type based on operation
        if operation == 'CREATE':
            # CREATE means object is in project but not in database
            drift_type = DriftType.MISSING_OBJECT
        elif operation == 'DROP':
            # DROP means object is in database but not in project
            drift_type = DriftType.EXTRA_OBJECT
        elif operation == 'ALTER':
            # ALTER means object exists in both but definition differs
            drift_type = DriftType.MODIFIED_OBJECT
        else:
            # Unknown operation type
            drift_type = DriftType.MODIFIED_OBJECT

        # Check if drift is acceptable
        acceptable = is_acceptable_drift(change, tolerance)

        if acceptable:
            drift_type = DriftType.ACCEPTABLE

        # Add categorization to change
        categorized_change = {
            **change,
            'drift_type': drift_type.value,
            'acceptable': acceptable
        }
        categorized.append(categorized_change)

    return categorized


def generate_drift_report(
    drift_data: Dict,
    categorized_changes: List[Dict],
    tolerance: str,
    environment: Dict,
    output_format: str = "table"
) -> str:
    """
    Generate human-readable drift report

    Args:
        drift_data: Dict from compare_database_to_project()
        categorized_changes: List from categorize_drift()
        tolerance: Tolerance level string
        environment: Dict with server, database info
        output_format: "table", "json", or "xml"

    Returns:
        Formatted report string
    """
    if output_format == "json":
        # Count drift types
        acceptable_count = sum(1 for c in categorized_changes if c['acceptable'])
        unacceptable_count = len(categorized_changes) - acceptable_count

        report = {
            "has_drift": drift_data.get('has_drift', False),
            "drift_count": drift_data.get('drift_count', 0),
            "acceptable_drift_count": acceptable_count,
            "unacceptable_drift_count": unacceptable_count,
            "tolerance": tolerance,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "environment": environment,
            "changes": categorized_changes
        }
        return json.dumps(report, indent=2)

    elif output_format == "xml":
        # Return the raw XML from sqlpackage
        return drift_data.get('report_xml', '')

    else:  # table format (default)
        lines = []

        # Group changes by acceptable/unacceptable
        unacceptable = [c for c in categorized_changes if not c['acceptable']]
        acceptable = [c for c in categorized_changes if c['acceptable']]

        if unacceptable:
            lines.append("UNACCEPTABLE DRIFT:")
            for change in unacceptable:
                operation = change['type']
                obj_type = change['object_type']
                obj_name = change['object_name']
                drift_type = change['drift_type']

                if drift_type == 'missing':
                    description = "Missing from database (defined in project)"
                elif drift_type == 'extra':
                    description = "Not present in SQL project (extra in database)"
                elif drift_type == 'modified':
                    description = "Definition differs between project and database"
                else:
                    description = "Schema difference detected"

                lines.append(f"  • {operation} {obj_type} [{obj_name}]")
                lines.append(f"    {description}")
            lines.append("")

        if acceptable:
            lines.append("ACCEPTABLE DRIFT:")
            for change in acceptable:
                operation = change['type']
                obj_type = change['object_type']
                obj_name = change['object_name']

                if obj_type == 'INDEX':
                    description = "Auto-generated performance index"
                elif obj_type == 'STATISTICS':
                    description = "Auto-generated statistics"
                else:
                    description = "Acceptable schema difference"

                lines.append(f"  • {operation} {obj_type} [{obj_name}]")
                lines.append(f"    {description}")

        return "\n".join(lines)


def generate_repair_migration(
    drift_data: Dict,
    migrations_dir: Path,
    database: str
) -> Tuple[Path, Path]:
    """
    Generate repair migration to fix detected drift

    Args:
        drift_data: Dict from compare_database_to_project()
        migrations_dir: Directory where migrations are stored
        database: Database name

    Returns:
        Tuple of (up_path, down_path)
    """
    from .migration_generator import generate_timestamp

    # Ensure migrations directory exists
    migrations_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = generate_timestamp()
    description = "repair_schema_drift"
    migration_id = f"{timestamp}_{description}"

    # Get script from drift data
    script = drift_data.get('script', '')

    # Build UP migration
    up_content = f"""-- Migration: {migration_id}
-- Type: REPAIR (Auto-generated drift repair)
-- Generated: {datetime.utcnow().isoformat()}Z
-- Purpose: Fix schema drift between database and SQL project
--
-- WARNING: This migration was auto-generated to repair drift.
-- Please review carefully before applying, especially DROP statements.

"""

    # Check if script contains DROP operations
    has_drops = 'DROP ' in script.upper()

    if has_drops:
        up_content += """-- ATTENTION: This migration contains DROP operations.
-- DROP statements have been commented out for safety.
-- Please review and uncomment only the operations you want to apply.
--
"""

        # Comment out DROP statements for safety
        lines = script.split('\n')
        modified_lines = []
        for line in lines:
            if 'DROP ' in line.upper():
                modified_lines.append(f"-- REVIEW REQUIRED: {line}")
            else:
                modified_lines.append(line)
        script = '\n'.join(modified_lines)

    up_content += script

    # For DOWN migration, we'd need to reverse the comparison
    # For now, create a template DOWN migration
    down_content = f"""-- Migration: {migration_id} (ROLLBACK)
-- Type: REPAIR ROLLBACK
-- Generated: {datetime.utcnow().isoformat()}Z
--
-- TODO: This is a template rollback migration.
-- To implement rollback, you need to reverse the drift repair operations.
-- This may require manual implementation depending on the changes.
--
-- Original drift repair applied expected state (SQL project) to database.
-- To rollback, you would need to reapply the database's original state.
-- This is complex and may not be reversible without data loss.
--
-- RECOMMENDATION: Take a database backup before applying drift repairs.

"""

    # Save migration files
    up_path = migrations_dir / f"{migration_id}.sql"
    down_path = migrations_dir / f"{migration_id}.down.sql"

    up_path.write_text(up_content, encoding='utf-8')
    down_path.write_text(down_content, encoding='utf-8')

    return up_path, down_path

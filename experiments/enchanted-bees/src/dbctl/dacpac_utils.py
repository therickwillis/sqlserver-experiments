"""
DACPAC utilities - Build and compare SQL Server DACPAC files
"""

import subprocess
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, List


def get_dacpac_hash(dacpac_path: Path) -> str:
    """Calculate SHA256 hash of a DACPAC file"""
    sha256_hash = hashlib.sha256()
    with open(dacpac_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def copy_baseline_dacpac(source_dacpac: Path, baseline_dir: Path) -> Path:
    """Copy current DACPAC as new baseline with hash in filename"""
    baseline_dir.mkdir(parents=True, exist_ok=True)

    # Calculate hash for filename
    dacpac_hash = get_dacpac_hash(source_dacpac)
    short_hash = dacpac_hash[:12]

    # Create baseline filename with hash
    baseline_name = f"{source_dacpac.stem}_{short_hash}.dacpac"
    baseline_path = baseline_dir / baseline_name

    # Copy the file
    shutil.copy2(source_dacpac, baseline_path)

    return baseline_path


def get_latest_baseline(baseline_dir: Path, project_name: str) -> Optional[Path]:
    """Get the most recent baseline DACPAC for a project"""
    if not baseline_dir.exists():
        return None

    # Find all baseline DACPACs for this project
    baselines = list(baseline_dir.glob(f"{project_name}_*.dacpac"))

    if not baselines:
        return None

    # Return the most recently modified
    return max(baselines, key=lambda p: p.stat().st_mtime)


def compare_dacpacs(source_dacpac: Path, target_dacpac: Path, output_file: Optional[Path] = None) -> Dict:
    """
    Compare two DACPACs using sqlpackage and return schema differences

    Args:
        source_dacpac: The new/source DACPAC (what we want to deploy)
        target_dacpac: The baseline/target DACPAC (current state)
        output_file: Optional path to save the deployment report XML

    Returns:
        Dict with comparison results including changes detected
    """
    if not source_dacpac.exists():
        raise FileNotFoundError(f"Source DACPAC not found: {source_dacpac}")
    if not target_dacpac.exists():
        raise FileNotFoundError(f"Target DACPAC not found: {target_dacpac}")

    # First, generate a deploy report to check for changes
    report_path = Path('/tmp/deploy_report.xml')
    script_path = Path('/tmp/migration.sql')

    # Generate deployment report
    report_cmd = [
        'sqlpackage',
        '/Action:DeployReport',
        f'/SourceFile:{source_dacpac}',
        f'/TargetFile:{target_dacpac}',
        f'/OutputPath:{report_path}',
        '/TargetDatabaseName:TempDB',  # Required parameter
        '/p:CommentOutSetVarDeclarations=True'
    ]

    try:
        result = subprocess.run(
            report_cmd,
            capture_output=True,
            text=True,
            check=False
        )

        # Check if there are changes by looking at the report file
        has_changes = False
        if report_path.exists():
            with open(report_path, 'r') as f:
                report_content = f.read()
                # Check if the report contains actual operations (not just header)
                has_changes = '<Operations>' in report_content and '</Operations>' in report_content
                # More robust check: see if there are any operation elements
                import re
                operations = re.findall(r'<Operation Name="([^"]+)"', report_content)
                has_changes = len(operations) > 0

        if not has_changes:
            return {
                'has_changes': False,
                'script': '',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        # If there are changes, generate the actual deployment script
        script_cmd = [
            'sqlpackage',
            '/Action:Script',
            f'/SourceFile:{source_dacpac}',
            f'/TargetFile:{target_dacpac}',
            f'/OutputPath:{script_path}',
            '/p:CommentOutSetVarDeclarations=True',
            '/p:IncludeTransactionalScripts=True',
            '/TargetDatabaseName:TempDB'  # Required for Script action
        ]

        script_result = subprocess.run(
            script_cmd,
            capture_output=True,
            text=True,
            check=False
        )

        # Read the generated script
        script_content = ""
        if script_path.exists():
            with open(script_path, 'r') as f:
                script_content = f.read()

        return {
            'has_changes': has_changes,
            'script': script_content,
            'stdout': result.stdout + '\n' + script_result.stdout,
            'stderr': result.stderr + '\n' + script_result.stderr,
            'returncode': script_result.returncode
        }

    except Exception as e:
        raise RuntimeError(f"Failed to compare DACPACs: {e}")


def parse_schema_changes(comparison_result: Dict) -> List[Dict]:
    """
    Parse the sqlpackage script output to extract individual schema changes

    Returns a list of change dictionaries with:
    - type: (CREATE, ALTER, DROP, etc.)
    - object_type: (TABLE, INDEX, CONSTRAINT, etc.)
    - object_name: name of the database object
    - sql: the SQL statement for this change
    """
    script = comparison_result.get('script', '')

    if not script:
        return []

    changes = []

    # Split by GO statements (SQL Server batch separator)
    batches = [b.strip() for b in script.split('\nGO\n') if b.strip()]

    for batch in batches:
        # Skip header comments and SETVAR declarations
        if batch.startswith('/*') or batch.startswith(':setvar') or batch.startswith('SET '):
            continue

        # Extract the operation type and object
        change = parse_sql_statement(batch)
        if change:
            changes.append(change)

    return changes


def parse_sql_statement(sql: str) -> Optional[Dict]:
    """Parse a single SQL statement to extract change information"""
    sql = sql.strip()

    if not sql:
        return None

    # Remove leading comments
    lines = sql.split('\n')
    first_statement_line = None
    for line in lines:
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('/*'):
            first_statement_line = line
            break

    if not first_statement_line:
        return None

    # Parse common patterns
    tokens = first_statement_line.upper().split()

    if len(tokens) < 2:
        return None

    operation = tokens[0]  # CREATE, ALTER, DROP, etc.

    # Skip control flow and non-DDL statements
    control_flow_keywords = ['IF', 'BEGIN', 'END', 'GO', 'PRINT', 'SET', 'USE',
                              'DECLARE', 'INSERT', 'UPDATE', 'DELETE', 'SELECT',
                              'ROLLBACK', 'COMMIT', ':ON', ':SETVAR']

    if operation in control_flow_keywords:
        return None

    # Determine object type
    object_type = None
    object_name = None

    if operation in ['CREATE', 'ALTER', 'DROP']:
        if len(tokens) >= 3:
            object_type = tokens[1]  # TABLE, INDEX, PROCEDURE, etc.

            # Skip temp tables
            if object_type == 'TABLE' and tokens[2].startswith('#'):
                return None

            # Object name is usually the third token (may need cleanup)
            object_name = tokens[2].strip('[]').replace('.', '_')

    return {
        'type': operation,
        'object_type': object_type,
        'object_name': object_name,
        'sql': sql
    }

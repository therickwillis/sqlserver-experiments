"""
Migration file generator - Create timestamp-based migration scripts
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def generate_timestamp() -> str:
    """Generate timestamp in YYYYMMDDHHMMSS format"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def generate_description(changes: List[Dict]) -> str:
    """
    Auto-generate a migration description from detected schema changes

    Examples:
    - Single table creation: "create_bees_table"
    - Multiple changes: "add_species_column_create_index"
    - Alterations: "alter_hive_table"
    """
    if not changes:
        return "empty_migration"

    # Count change types
    creates = [c for c in changes if c.get('type') == 'CREATE']
    alters = [c for c in changes if c.get('type') == 'ALTER']
    drops = [c for c in changes if c.get('type') == 'DROP']

    description_parts = []

    # Describe creates
    if creates:
        if len(creates) == 1:
            change = creates[0]
            obj_type = change.get('object_type', 'object').lower()
            obj_name = change.get('object_name', '').lower()
            if obj_name:
                description_parts.append(f"create_{obj_name}")
            else:
                description_parts.append(f"create_{obj_type}")
        else:
            # Multiple creates
            tables = [c for c in creates if c.get('object_type') == 'TABLE']
            if tables:
                description_parts.append(f"create_{len(tables)}_tables")
            else:
                description_parts.append(f"create_{len(creates)}_objects")

    # Describe alters
    if alters:
        if len(alters) == 1 and not creates and not drops:
            change = alters[0]
            obj_name = change.get('object_name', '').lower()
            if obj_name:
                description_parts.append(f"alter_{obj_name}")
            else:
                description_parts.append("alter_schema")
        else:
            description_parts.append(f"alter_{len(alters)}_objects")

    # Describe drops
    if drops:
        if len(drops) == 1 and not creates and not alters:
            change = drops[0]
            obj_name = change.get('object_name', '').lower()
            if obj_name:
                description_parts.append(f"drop_{obj_name}")
            else:
                description_parts.append("drop_object")
        else:
            description_parts.append(f"drop_{len(drops)}_objects")

    # Combine parts
    if description_parts:
        description = "_".join(description_parts)
    else:
        description = "schema_changes"

    # Sanitize description (remove special chars, limit length)
    description = description.replace('[', '').replace(']', '').replace('.', '_')
    description = description[:80]  # Limit length

    return description


def generate_metadata_header(
    timestamp: str,
    description: str,
    baseline_hash: str,
    script_content: str
) -> str:
    """
    Generate metadata header for migration file

    Includes:
    - Timestamp
    - Description
    - Baseline DACPAC hash reference
    - Migration script checksum
    """
    # Calculate checksum of the script content
    checksum = hashlib.sha256(script_content.encode()).hexdigest()

    header = f"""-- =============================================
-- Migration: {timestamp}_{description}
-- Generated: {datetime.now().isoformat()}
-- Baseline DACPAC: {baseline_hash}
-- Checksum: {checksum}
-- =============================================
"""
    return header


def generate_up_migration(
    changes: List[Dict],
    script: str,
    timestamp: str,
    description: str,
    baseline_hash: str
) -> str:
    """
    Generate UP migration script with metadata header

    Args:
        changes: Parsed schema changes
        script: Raw SQL script from sqlpackage
        timestamp: Migration timestamp
        description: Migration description
        baseline_hash: Hash of baseline DACPAC

    Returns:
        Complete UP migration script with header
    """
    # Clean up the script (remove sqlpackage headers/comments)
    clean_script = clean_sqlpackage_script(script)

    # Generate metadata header
    header = generate_metadata_header(timestamp, description, baseline_hash, clean_script)

    # Combine header and script
    up_migration = header + "\n" + clean_script

    return up_migration


def generate_down_migration(
    changes: List[Dict],
    timestamp: str,
    description: str
) -> Optional[str]:
    """
    Generate DOWN (rollback) migration script for reversible changes

    Returns None if changes are not automatically reversible

    Reversible changes:
    - CREATE TABLE -> DROP TABLE
    - ADD COLUMN -> DROP COLUMN
    - CREATE INDEX -> DROP INDEX
    - DROP INDEX -> CREATE INDEX (if we have the definition)

    Not reversible (require manual intervention):
    - DROP TABLE (data loss)
    - DROP COLUMN (data loss)
    - ALTER COLUMN (type changes, data conversion)
    - Complex refactorings
    """
    reversible_statements = []
    is_fully_reversible = True

    for change in changes:
        operation = change.get('type')
        object_type = change.get('object_type')
        object_name = change.get('object_name')

        # Check if this change is reversible
        if operation == 'CREATE':
            if object_type in ['TABLE', 'INDEX', 'VIEW', 'PROCEDURE', 'FUNCTION']:
                # Can be reversed with DROP
                reversible_statements.append(f"DROP {object_type} IF EXISTS [{object_name}];")
            else:
                is_fully_reversible = False

        elif operation == 'DROP':
            # Drops are usually not reversible (data loss)
            is_fully_reversible = False

        elif operation == 'ALTER':
            # Alters are complex and usually not auto-reversible
            is_fully_reversible = False

        else:
            is_fully_reversible = False

    # If not fully reversible, return template
    if not is_fully_reversible:
        return generate_down_migration_template(changes, timestamp, description)

    # Generate the DOWN migration
    header = f"""-- =============================================
-- Rollback Migration: {timestamp}_{description}
-- Generated: {datetime.now().isoformat()}
-- WARNING: This rollback script was auto-generated.
-- Review carefully before executing.
-- =============================================

"""

    script = header + "\n".join(reversed(reversible_statements))

    return script


def generate_down_migration_template(
    changes: List[Dict],
    timestamp: str,
    description: str
) -> str:
    """
    Generate a template for manual DOWN migration creation

    Used when changes are not automatically reversible
    """
    header = f"""-- =============================================
-- Rollback Migration: {timestamp}_{description}
-- Generated: {datetime.now().isoformat()}
-- =============================================
-- WARNING: This migration contains changes that cannot be automatically reversed.
-- You must manually implement the rollback logic below.
--
-- Changes in this migration:
"""

    # Document what changed
    change_docs = []
    for change in changes:
        operation = change.get('type')
        object_type = change.get('object_type')
        object_name = change.get('object_name')
        change_docs.append(f"--   - {operation} {object_type} [{object_name}]")

    footer = """--
-- TODO: Implement rollback logic below
-- =============================================

-- Your rollback SQL here
"""

    return header + "\n".join(change_docs) + "\n" + footer


def clean_sqlpackage_script(script: str) -> str:
    """
    Clean up sqlpackage-generated script

    Removes:
    - Header comments
    - SETVAR declarations
    - Excessive blank lines
    """
    lines = script.split('\n')
    cleaned_lines = []

    skip_header = True
    previous_blank = False

    for line in lines:
        stripped = line.strip()

        # Skip header section until we hit actual SQL
        if skip_header:
            if stripped.startswith(':setvar') or stripped.startswith('SET ') or stripped.startswith('/*'):
                continue
            elif stripped and not stripped.startswith('--'):
                skip_header = False

        # Skip excessive blank lines
        if not stripped:
            if previous_blank:
                continue
            previous_blank = True
        else:
            previous_blank = False

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


def save_migration_files(
    migrations_dir: Path,
    timestamp: str,
    description: str,
    up_script: str,
    down_script: Optional[str] = None
) -> Tuple[Path, Optional[Path]]:
    """
    Save migration files to disk

    Returns:
        Tuple of (up_file_path, down_file_path)
    """
    migrations_dir.mkdir(parents=True, exist_ok=True)

    # UP migration file
    up_filename = f"{timestamp}_{description}.sql"
    up_path = migrations_dir / up_filename

    with open(up_path, 'w') as f:
        f.write(up_script)

    # DOWN migration file (if provided)
    down_path = None
    if down_script:
        down_filename = f"{timestamp}_{description}.down.sql"
        down_path = migrations_dir / down_filename

        with open(down_path, 'w') as f:
            f.write(down_script)

    return up_path, down_path

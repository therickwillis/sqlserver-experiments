"""
Rollback executor - Discover, validate, and execute rollback (.down.sql) scripts
"""

import pyodbc
import time
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .migration_tracker import (
    calculate_file_checksum,
    get_applied_migrations_for_rollback,
    record_rollback,
    validate_rollback_eligible,
    acquire_migration_lock,
    release_migration_lock
)
from .migration_executor import read_migration_sql, _execute_sql_via_pyodbc


def discover_down_migrations(migrations_dir: Path) -> List[Dict]:
    """
    Discover all .down.sql files in the migrations directory

    Args:
        migrations_dir: Path to migrations directory

    Returns:
        List of down migration dicts, each containing:
        - file_path: Path to the .down.sql file
        - migration_id: Migration identifier (filename without .down.sql)
        - timestamp: Migration timestamp (from filename)
        - description: Migration description
        - checksum: SHA256 checksum of the file
        - is_template: Boolean indicating if file contains TODO marker
    """
    if not migrations_dir.exists():
        return []

    down_migrations = []

    # Find all .down.sql files
    for down_file in sorted(migrations_dir.glob("*.down.sql")):
        # Parse filename: YYYYMMDDHHMMSS_description.down.sql
        # Remove .down.sql to get migration_id
        migration_id = down_file.stem.replace('.down', '')
        parts = migration_id.split('_', 1)

        if len(parts) != 2:
            continue  # Skip malformed filenames

        timestamp, description = parts

        # Validate timestamp format
        if len(timestamp) != 14 or not timestamp.isdigit():
            continue  # Skip invalid timestamps

        # Check if file is a template (contains TODO marker)
        try:
            with open(down_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                is_template = 'TODO' in content.upper()
        except Exception:
            is_template = True  # If we can't read it, treat as template

        down_migrations.append({
            'file_path': down_file,
            'migration_id': migration_id,
            'timestamp': timestamp,
            'description': description,
            'checksum': calculate_file_checksum(down_file),
            'is_template': is_template
        })

    # Sort by timestamp
    down_migrations.sort(key=lambda m: m['timestamp'])

    return down_migrations


def validate_down_migration(down_file: Path) -> Tuple[bool, Optional[str], bool]:
    """
    Validate a .down.sql file

    Args:
        down_file: Path to .down.sql file

    Returns:
        Tuple of (is_valid, error_message, is_template)
        - is_valid: True if file is valid for rollback, False otherwise
        - error_message: None if valid, otherwise contains error details
        - is_template: True if file contains TODO marker (requires manual implementation)
    """
    # Check file exists
    if not down_file.exists():
        return (False, f"Down migration file not found: {down_file}", False)

    # Check file is readable and not empty
    try:
        with open(down_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        if not content.strip():
            return (False, f"Down migration file is empty: {down_file}", False)

        # Check if it's a template (contains TODO marker)
        is_template = 'TODO' in content.upper()

        if is_template:
            return (False,
                    f"Down migration is a template requiring manual implementation: {down_file}\n"
                    f"Edit the file to implement the rollback logic, then remove the TODO marker.",
                    True)

        return (True, None, False)

    except Exception as e:
        return (False, f"Failed to read down migration file: {e}", False)


def execute_rollback(
    conn: pyodbc.Connection,
    migration: Dict,
    down_file_path: Path
) -> Tuple[bool, Optional[str], int]:
    """
    Execute a single rollback script via pyodbc

    Args:
        conn: Active database connection (used only for recording rollback)
        migration: Migration dict with migration_id
        down_file_path: Path to the .down.sql file

    Returns:
        Tuple of (success: bool, error_message: Optional[str], execution_time_ms: int)
    """
    migration_id = migration['migration_id']

    # Get connection parameters from environment
    server = os.getenv('DB_SERVER', 'sqlserver')
    port = os.getenv('DB_PORT', '1433')
    database = os.getenv('DB_NAME', 'EnchantedBeesDB')
    user = os.getenv('DB_USER', 'sa')
    password = os.getenv('DB_PASSWORD', '')

    # Build server string
    target_server = f"{server},{port}" if port else server

    # Read and clean the rollback SQL
    try:
        sql = read_migration_sql(down_file_path)
    except Exception as e:
        return False, f"Failed to read rollback file: {e}", 0

    start_time = time.time()

    try:
        _execute_sql_via_pyodbc(sql, target_server, database, user, password)

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Record successful rollback
        record_rollback(conn, migration_id, execution_time_ms)

        return True, None, execution_time_ms

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Rollback failed: {str(e)}"
        return False, error_message, execution_time_ms


def execute_rollbacks(
    migrations_dir: Path,
    conn: pyodbc.Connection,
    count: int,
    dry_run: bool = False,
    lock_timeout: int = 30
) -> Dict:
    """
    Execute rollback for the last N migrations

    Args:
        migrations_dir: Path to migrations directory
        conn: Active database connection
        count: Number of migrations to rollback (from most recent)
        dry_run: If True, only show what would be done
        lock_timeout: Timeout for acquiring migration lock (seconds)

    Returns:
        Dict with:
        - rollback_count: Number of migrations to rollback
        - successful_count: Number successfully rolled back
        - failed_count: Number that failed
        - rollbacks: List of rollback result dicts
        - errors: List of error messages
    """
    # Initialize result
    result = {
        'rollback_count': 0,
        'successful_count': 0,
        'failed_count': 0,
        'rollbacks': [],
        'errors': []
    }

    # Get applied migrations in reverse chronological order
    applied_migrations = get_applied_migrations_for_rollback(conn)

    # Limit to the requested count
    migrations_to_rollback = applied_migrations[:count]
    result['rollback_count'] = len(migrations_to_rollback)

    if len(migrations_to_rollback) == 0:
        result['errors'].append("No migrations available to rollback")
        return result

    # Build a map of down migrations
    down_migrations_map = {}
    for down_mig in discover_down_migrations(migrations_dir):
        down_migrations_map[down_mig['migration_id']] = down_mig

    # Validate all rollbacks before executing
    validation_errors = []
    for migration in migrations_to_rollback:
        migration_id = migration['migration_id']

        # Check if down file exists
        if migration_id not in down_migrations_map:
            down_file_path = migrations_dir / f"{migration_id}.down.sql"
            validation_errors.append(
                f"Cannot rollback '{migration_id}': .down.sql file not found at {down_file_path}"
            )
            continue

        down_migration = down_migrations_map[migration_id]

        # Validate the down file
        is_valid, error_msg, is_template = validate_down_migration(down_migration['file_path'])

        if not is_valid:
            validation_errors.append(error_msg)

    # If any validation errors and not dry-run, fail early
    if validation_errors:
        result['errors'].extend(validation_errors)
        result['failed_count'] = len(validation_errors)
        return result

    # If dry-run, just return the plan
    if dry_run:
        for migration in migrations_to_rollback:
            migration_id = migration['migration_id']
            down_migration = down_migrations_map.get(migration_id)

            result['rollbacks'].append({
                'migration_id': migration_id,
                'description': migration_id.split('_', 1)[1] if '_' in migration_id else migration_id,
                'down_file': str(down_migration['file_path']) if down_migration else 'NOT FOUND',
                'status': 'can_rollback' if down_migration and not down_migration['is_template'] else 'cannot_rollback',
                'execution_time_ms': 0,
                'error': None
            })

        return result

    # Execute rollbacks (not dry-run)
    lock_acquired = False
    try:
        # Acquire migration lock
        lock_acquired = acquire_migration_lock(conn, lock_timeout)

        if not lock_acquired:
            result['errors'].append(
                f"Could not acquire migration lock after {lock_timeout} seconds. "
                "Another migration or rollback may be in progress."
            )
            return result

        # Execute each rollback in order
        for migration in migrations_to_rollback:
            migration_id = migration['migration_id']
            down_migration = down_migrations_map[migration_id]

            # Validate rollback eligibility
            is_eligible, error_msg = validate_rollback_eligible(conn, migration_id)

            if not is_eligible:
                result['errors'].append(error_msg)
                result['failed_count'] += 1
                result['rollbacks'].append({
                    'migration_id': migration_id,
                    'description': migration_id.split('_', 1)[1] if '_' in migration_id else migration_id,
                    'status': 'failed',
                    'execution_time_ms': 0,
                    'error': error_msg
                })
                break  # Stop on first failure

            # Execute the rollback
            success, error, exec_time = execute_rollback(
                conn,
                migration,
                down_migration['file_path']
            )

            rollback_result = {
                'migration_id': migration_id,
                'description': migration_id.split('_', 1)[1] if '_' in migration_id else migration_id,
                'execution_time_ms': exec_time,
                'status': 'rolled_back' if success else 'failed',
                'error': error
            }

            result['rollbacks'].append(rollback_result)

            if success:
                result['successful_count'] += 1
            else:
                result['failed_count'] += 1
                result['errors'].append(f"Rollback of '{migration_id}' failed: {error}")
                break  # Stop on first failure

    finally:
        # Always release the lock
        if lock_acquired:
            release_migration_lock(conn)

    return result


def get_rollbackable_migrations(
    migrations_dir: Path,
    conn: pyodbc.Connection,
    count: Optional[int] = None
) -> List[Dict]:
    """
    Get list of migrations that can be rolled back

    Args:
        migrations_dir: Path to migrations directory
        conn: Active database connection
        count: Maximum number to return (None = all)

    Returns:
        List of dicts with:
        - migration_id
        - description
        - applied_at
        - has_down_file: Boolean
        - down_file_is_template: Boolean
        - can_rollback: Boolean (has down file and not template)
    """
    # Get applied migrations in reverse chronological order
    applied_migrations = get_applied_migrations_for_rollback(conn)

    if count is not None:
        applied_migrations = applied_migrations[:count]

    # Build a map of down migrations
    down_migrations_map = {}
    for down_mig in discover_down_migrations(migrations_dir):
        down_migrations_map[down_mig['migration_id']] = down_mig

    # Build result list
    rollbackable = []
    for migration in applied_migrations:
        migration_id = migration['migration_id']
        down_migration = down_migrations_map.get(migration_id)

        has_down_file = down_migration is not None
        down_file_is_template = down_migration['is_template'] if down_migration else False
        can_rollback = has_down_file and not down_file_is_template

        rollbackable.append({
            'migration_id': migration_id,
            'description': migration_id.split('_', 1)[1] if '_' in migration_id else migration_id,
            'applied_at': migration['applied_at'],
            'has_down_file': has_down_file,
            'down_file_is_template': down_file_is_template,
            'can_rollback': can_rollback
        })

    return rollbackable

"""
Migration executor - Discover, validate, and execute migration scripts
"""

import pyodbc
import re
import time
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .migration_tracker import (
    calculate_file_checksum,
    get_applied_migrations,
    get_connection_string,
    is_migration_applied,
    validate_migration_checksum,
    record_migration,
    acquire_migration_lock,
    release_migration_lock
)


def discover_migrations(migrations_dir: Path) -> List[Dict]:
    """
    Discover all migration files in the migrations directory

    Args:
        migrations_dir: Path to migrations directory

    Returns:
        List of migration dicts sorted by timestamp, each containing:
        - file_path: Path to the migration file
        - migration_id: Migration identifier (filename without .sql)
        - timestamp: Migration timestamp (from filename)
        - description: Migration description
        - checksum: SHA256 checksum of the file
    """
    if not migrations_dir.exists():
        return []

    migrations = []

    # Find all .sql files (excluding .down.sql files)
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name.endswith('.down.sql'):
            continue

        # Parse filename: YYYYMMDDHHMMSS_description.sql
        migration_id = sql_file.stem  # Remove .sql extension
        parts = migration_id.split('_', 1)

        if len(parts) != 2:
            continue  # Skip malformed filenames

        timestamp, description = parts

        # Validate timestamp format
        if len(timestamp) != 14 or not timestamp.isdigit():
            continue  # Skip invalid timestamps

        migrations.append({
            'file_path': sql_file,
            'migration_id': migration_id,
            'timestamp': timestamp,
            'description': description,
            'checksum': calculate_file_checksum(sql_file)
        })

    # Sort by timestamp (already sorted by filename, but explicit is better)
    migrations.sort(key=lambda m: m['timestamp'])

    return migrations


def get_pending_migrations(
    migrations_dir: Path,
    conn: pyodbc.Connection
) -> List[Dict]:
    """
    Get list of migrations that haven't been applied yet

    Args:
        migrations_dir: Path to migrations directory
        conn: Active database connection

    Returns:
        List of pending migration dicts
    """
    all_migrations = discover_migrations(migrations_dir)
    applied = get_applied_migrations(conn)
    applied_ids = {m['migration_id'] for m in applied}

    pending = [m for m in all_migrations if m['migration_id'] not in applied_ids]

    return pending


def validate_migration_integrity(
    migrations_dir: Path,
    conn: pyodbc.Connection
) -> Tuple[bool, List[str]]:
    """
    Validate that all applied migrations haven't been tampered with

    Args:
        migrations_dir: Path to migrations directory
        conn: Active database connection

    Returns:
        Tuple of (all_valid: bool, errors: List[str])
    """
    all_migrations = discover_migrations(migrations_dir)
    errors = []

    for migration in all_migrations:
        migration_id = migration['migration_id']
        current_checksum = migration['checksum']

        try:
            validate_migration_checksum(conn, migration_id, current_checksum)
        except ValueError as e:
            errors.append(str(e))

    return len(errors) == 0, errors


def read_migration_sql(file_path: Path) -> str:
    """
    Read migration SQL from file and remove SQLCMD-specific syntax

    Args:
        file_path: Path to migration SQL file

    Returns:
        SQL content as string with SQLCMD commands removed
    """
    import re

    with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM at start
        content = f.read()

    # Remove any BOM characters that might be embedded in the file (sqlpackage sometimes adds them)
    content = content.replace('\ufeff', '')

    # Remove SQLCMD variable definitions and checks
    # Remove :setvar commands
    content = re.sub(r'^:setvar\s+.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Remove :on error exit
    content = re.sub(r'^:on\s+error\s+exit.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Remove the SQLCMD mode check block
    # This is the IF N'$(__IsSqlCmdEnabled)' NOT LIKE N'True' BEGIN ... END block
    sqlcmd_check_pattern = r"IF\s+N'\$\(__IsSqlCmdEnabled\)'\s+NOT\s+LIKE\s+N'True'\s+BEGIN.*?END"
    content = re.sub(sqlcmd_check_pattern, '', content, flags=re.DOTALL | re.IGNORECASE)

    # Remove USE [$(DatabaseName)] which relies on SQLCMD variables
    content = re.sub(r'USE\s+\[\$\(DatabaseName\)\]', '', content, flags=re.IGNORECASE)

    return content


def _split_sql_batches(sql: str) -> List[str]:
    """
    Split SQL script on GO batch separators.

    GO must appear on its own line (with optional whitespace).

    Args:
        sql: Full SQL script content

    Returns:
        List of SQL batch strings (empty batches excluded)
    """
    batches = re.split(r'^\s*GO\s*$', sql, flags=re.MULTILINE | re.IGNORECASE)
    return [b.strip() for b in batches if b.strip()]


def _execute_sql_via_pyodbc(sql: str, server: str, database: str, user: str, password: str) -> None:
    """
    Execute a SQL script (with GO batch separators) via pyodbc.

    Creates a dedicated autocommit connection so that scripts which manage
    their own transactions work correctly.

    Args:
        sql: SQL script content (may contain GO separators)
        server: Server connection string (host,port)
        database: Target database name
        user: SQL login username
        password: SQL login password

    Raises:
        Exception on any execution error
    """
    conn_str = get_connection_string(server, database, user, password)
    exec_conn = pyodbc.connect(conn_str, autocommit=True)
    try:
        cursor = exec_conn.cursor()
        try:
            for batch in _split_sql_batches(sql):
                cursor.execute(batch)
        finally:
            cursor.close()
    finally:
        exec_conn.close()


def execute_migration(
    conn: pyodbc.Connection,
    migration: Dict,
    transactional: bool = True
) -> Tuple[bool, Optional[str], int]:
    """
    Execute a single migration script via pyodbc

    Args:
        conn: Active database connection (used only for recording migration)
        migration: Migration dict with file_path, migration_id, checksum
        transactional: Whether to wrap in a transaction (ignored - sqlpackage scripts manage their own)

    Returns:
        Tuple of (success: bool, error_message: Optional[str], execution_time_ms: int)
    """
    migration_id = migration['migration_id']
    file_path = migration['file_path']
    checksum = migration['checksum']

    # Get connection parameters from environment
    server = os.getenv('DB_SERVER', 'sqlserver')
    port = os.getenv('DB_PORT', '1433')
    database = os.getenv('DB_NAME', 'EnchantedBeesDB')
    user = os.getenv('DB_USER', 'sa')
    password = os.getenv('DB_PASSWORD', '')

    # Build server string
    target_server = f"{server},{port}" if port else server

    # Read and clean the migration SQL
    try:
        sql = read_migration_sql(file_path)
    except Exception as e:
        return False, f"Failed to read migration file: {e}", 0

    start_time = time.time()

    try:
        _execute_sql_via_pyodbc(sql, target_server, database, user, password)

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Migration succeeded - record it in __MigrationsHistory
        record_migration(conn, migration_id, checksum, execution_time_ms)

        return True, None, execution_time_ms

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Migration failed: {str(e)}"
        return False, error_message, execution_time_ms




def execute_pending_migrations(
    migrations_dir: Path,
    conn: pyodbc.Connection,
    dry_run: bool = False,
    lock_timeout: int = 30
) -> Dict:
    """
    Execute all pending migrations

    Args:
        migrations_dir: Path to migrations directory
        conn: Active database connection
        dry_run: If True, only show what would be done without executing
        lock_timeout: Timeout in seconds for acquiring migration lock

    Returns:
        Dict with execution results:
        - pending_count: Number of pending migrations
        - applied_count: Number successfully applied
        - failed_count: Number that failed
        - migrations: List of migration results
        - errors: List of error messages
    """
    pending = get_pending_migrations(migrations_dir, conn)

    result = {
        'pending_count': len(pending),
        'applied_count': 0,
        'failed_count': 0,
        'migrations': [],
        'errors': []
    }

    if len(pending) == 0:
        return result

    if dry_run:
        # Just return the list of pending migrations
        result['migrations'] = [
            {
                'migration_id': m['migration_id'],
                'description': m['description'],
                'status': 'pending'
            }
            for m in pending
        ]
        return result

    # Acquire lock to prevent concurrent migrations
    lock_acquired = acquire_migration_lock(conn, lock_timeout)

    if not lock_acquired:
        result['errors'].append(
            f"Could not acquire migration lock after {lock_timeout} seconds. "
            "Another migration may be in progress."
        )
        return result

    try:
        # Execute each pending migration
        for migration in pending:
            migration_id = migration['migration_id']
            description = migration['description']

            success, error, exec_time = execute_migration(conn, migration, transactional=True)

            migration_result = {
                'migration_id': migration_id,
                'description': description,
                'execution_time_ms': exec_time,
                'status': 'applied' if success else 'failed',
                'error': error
            }

            result['migrations'].append(migration_result)

            if success:
                result['applied_count'] += 1
            else:
                result['failed_count'] += 1
                result['errors'].append(f"{migration_id}: {error}")

                # Stop on first failure
                break

    finally:
        # Always release the lock
        release_migration_lock(conn)

    return result

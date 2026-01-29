"""
Migration tracker - Manage __MigrationsHistory table and track applied migrations
"""

import hashlib
import pyodbc
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


# SQL to create migrations history table
CREATE_MIGRATIONS_HISTORY_TABLE = """
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '__MigrationsHistory' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE [dbo].[__MigrationsHistory] (
        [MigrationId] NVARCHAR(150) NOT NULL PRIMARY KEY,
        [Checksum] NVARCHAR(64) NOT NULL,
        [AppliedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [AppliedBy] NVARCHAR(100) NOT NULL,
        [ExecutionTimeMs] INT NOT NULL,
        [Success] BIT NOT NULL DEFAULT 1
    );
END
"""


def get_connection_string(server: str, database: str, user: str, password: str) -> str:
    """Build SQL Server connection string"""
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )


def ensure_migrations_history_table(conn: pyodbc.Connection) -> None:
    """
    Ensure the __MigrationsHistory table exists

    Args:
        conn: Active database connection
    """
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_MIGRATIONS_HISTORY_TABLE)
        conn.commit()
    finally:
        cursor.close()


def get_applied_migrations(conn: pyodbc.Connection) -> List[Dict]:
    """
    Get list of all applied migrations from the database

    Args:
        conn: Active database connection

    Returns:
        List of dicts with migration info (MigrationId, Checksum, AppliedAt, etc.)
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                MigrationId,
                Checksum,
                AppliedAt,
                AppliedBy,
                ExecutionTimeMs,
                Success
            FROM [dbo].[__MigrationsHistory]
            WHERE Success = 1
            ORDER BY MigrationId
        """)

        migrations = []
        for row in cursor.fetchall():
            migrations.append({
                'migration_id': row.MigrationId,
                'checksum': row.Checksum,
                'applied_at': row.AppliedAt,
                'applied_by': row.AppliedBy,
                'execution_time_ms': row.ExecutionTimeMs,
                'success': bool(row.Success)
            })

        return migrations

    finally:
        cursor.close()


def record_migration(
    conn: pyodbc.Connection,
    migration_id: str,
    checksum: str,
    execution_time_ms: int,
    applied_by: str = 'dbctl'
) -> None:
    """
    Record a successfully applied migration

    Args:
        conn: Active database connection
        migration_id: Migration identifier (e.g., "20260127043356_add_hive_table")
        checksum: SHA256 checksum of the migration file
        execution_time_ms: Execution time in milliseconds
        applied_by: Tool/user that applied the migration
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO [dbo].[__MigrationsHistory]
            (MigrationId, Checksum, AppliedAt, AppliedBy, ExecutionTimeMs, Success)
            VALUES (?, ?, GETUTCDATE(), ?, ?, 1)
        """, (migration_id, checksum, applied_by, execution_time_ms))

        conn.commit()

    finally:
        cursor.close()


def is_migration_applied(conn: pyodbc.Connection, migration_id: str) -> bool:
    """
    Check if a migration has already been applied

    Args:
        conn: Active database connection
        migration_id: Migration identifier to check

    Returns:
        True if migration is already applied, False otherwise
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM [dbo].[__MigrationsHistory]
            WHERE MigrationId = ? AND Success = 1
        """, (migration_id,))

        count = cursor.fetchone()[0]
        return count > 0

    finally:
        cursor.close()


def validate_migration_checksum(
    conn: pyodbc.Connection,
    migration_id: str,
    current_checksum: str
) -> bool:
    """
    Validate that a migration's checksum hasn't changed since it was applied

    Args:
        conn: Active database connection
        migration_id: Migration identifier
        current_checksum: Current checksum of the migration file

    Returns:
        True if checksums match or migration not applied, False if tampered

    Raises:
        ValueError: If migration was applied but checksum doesn't match
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT Checksum
            FROM [dbo].[__MigrationsHistory]
            WHERE MigrationId = ? AND Success = 1
        """, (migration_id,))

        row = cursor.fetchone()

        if row is None:
            # Migration not applied yet, no validation needed
            return True

        stored_checksum = row.Checksum

        if stored_checksum != current_checksum:
            raise ValueError(
                f"Migration '{migration_id}' has been tampered with!\n"
                f"Stored checksum:  {stored_checksum}\n"
                f"Current checksum: {current_checksum}\n"
                f"DO NOT apply this migration. Investigate the changes."
            )

        return True

    finally:
        cursor.close()


def calculate_file_checksum(file_path: Path) -> str:
    """
    Calculate SHA256 checksum of a file

    Args:
        file_path: Path to the file

    Returns:
        Hex string of the SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def acquire_migration_lock(conn: pyodbc.Connection, timeout_seconds: int = 30) -> bool:
    """
    Acquire an application lock to prevent concurrent migrations

    Uses SQL Server's sp_getapplock to ensure only one migration runs at a time

    Args:
        conn: Active database connection
        timeout_seconds: How long to wait for the lock

    Returns:
        True if lock acquired, False if timeout

    Raises:
        RuntimeError: If lock acquisition fails
    """
    cursor = conn.cursor()
    try:
        # sp_getapplock returns:
        #  >= 0: Lock granted
        #  -1: Timeout
        #  -2: Cancelled
        #  -3: Deadlock victim
        #  -999: Parameter error
        cursor.execute("""
            DECLARE @result INT;
            EXEC @result = sp_getapplock
                @Resource = 'DbctlMigrationLock',
                @LockMode = 'Exclusive',
                @LockOwner = 'Session',
                @LockTimeout = ?;
            SELECT @result;
        """, (timeout_seconds * 1000,))  # Convert to milliseconds

        result = cursor.fetchone()[0]

        if result >= 0:
            return True
        elif result == -1:
            return False  # Timeout
        else:
            raise RuntimeError(f"Failed to acquire migration lock (code: {result})")

    finally:
        cursor.close()


def release_migration_lock(conn: pyodbc.Connection) -> None:
    """
    Release the migration application lock

    Args:
        conn: Active database connection
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            EXEC sp_releaseapplock
                @Resource = 'DbctlMigrationLock',
                @LockOwner = 'Session';
        """)
    finally:
        cursor.close()

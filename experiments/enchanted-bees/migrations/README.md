# Migrations Directory

Timestamp-based migration scripts generated from SQL project changes.

## Structure
- UP migrations: `YYYYMMDDHHMMSS_description.sql`
- DOWN migrations: `YYYYMMDDHHMMSS_description.down.sql`

## Metadata
Each migration includes metadata in SQL comment headers:
- Timestamp
- Baseline DACPAC reference
- Checksum for integrity validation


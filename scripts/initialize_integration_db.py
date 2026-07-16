from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"
SCHEMA_PATH = ROOT / "sql" / "integration" / "001_create_integration_schema.sql"

DATABASE_VERSION = "0.5.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema SQL not found: {SCHEMA_PATH}")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        connection.execute(schema_sql)

        existing = connection.execute(
            """
            SELECT COUNT(*)
            FROM meta.database_version
            WHERE version = ?
            """,
            [DATABASE_VERSION],
        ).fetchone()[0]

        if existing == 0:
            connection.execute(
                """
                INSERT INTO meta.database_version (
                    version,
                    applied_at_utc,
                    description
                )
                VALUES (?, ?, ?)
                """,
                [
                    DATABASE_VERSION,
                    utc_now(),
                    "Initial Phase 0.5 integration database schema",
                ],
            )

        table_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema IN ('meta', 'registry', 'contracts')
              AND table_type = 'BASE TABLE'
            """
        ).fetchone()[0]

        view_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'analytics'
              AND table_type = 'VIEW'
            """
        ).fetchone()[0]

    print("Integration database initialized successfully.")
    print(f"Database: {DATABASE_PATH}")
    print(f"Database version: {DATABASE_VERSION}")
    print(f"Base tables: {table_count}")
    print(f"Analytical views: {view_count}")


if __name__ == "__main__":
    main()
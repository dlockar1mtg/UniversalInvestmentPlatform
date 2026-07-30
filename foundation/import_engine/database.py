"""DuckDB database management for the Universal Import Engine."""

from __future__ import annotations

from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.migrations import apply_ordered_migrations


def initialize_database(config: ImportEngineConfig) -> None:
    """Create or upgrade the Universal DuckDB database."""

    apply_ordered_migrations(config)


def list_database_objects(config: ImportEngineConfig) -> list[tuple[str, str]]:
    """Return database table and view names."""

    connection = duckdb.connect(str(config.database_path), read_only=True)

    try:
        rows = connection.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_type, table_name
            """
        ).fetchall()

        return [(str(name), str(object_type)) for name, object_type in rows]
    finally:
        connection.close()


def get_table_count(config: ImportEngineConfig, table_name: str) -> int:
    """Return the row count for a trusted internal table name."""

    allowed_characters = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    )

    if not table_name or any(char not in allowed_characters for char in table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    connection = duckdb.connect(str(config.database_path), read_only=True)

    try:
        result = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()

        return int(result[0])
    finally:
        connection.close()
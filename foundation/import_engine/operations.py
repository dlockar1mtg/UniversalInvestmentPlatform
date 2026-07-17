"""Operational inspection helpers for imports and registry health."""

from __future__ import annotations

import duckdb

from foundation.import_engine.config import ImportEngineConfig


def fetch_platform_health(config: ImportEngineConfig):
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        return connection.execute(
            """
            SELECT *
            FROM universal_import_health
            ORDER BY platform_id
            """
        ).fetchdf()
    finally:
        connection.close()


def fetch_recent_imports(config: ImportEngineConfig, limit: int = 20):
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        return connection.execute(
            """
            SELECT
                import_id,
                package_id,
                platform_id,
                import_mode,
                import_status,
                started_at_utc,
                completed_at_utc,
                dataset_count,
                imported_row_count,
                warning_count,
                error_count,
                error_summary
            FROM universal_imports
            ORDER BY started_at_utc DESC NULLS LAST
            LIMIT ?
            """,
            [limit],
        ).fetchdf()
    finally:
        connection.close()


def fetch_recent_errors(config: ImportEngineConfig, limit: int = 20):
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        return connection.execute(
            """
            SELECT
                import_id,
                severity,
                error_code,
                error_message,
                created_at_utc
            FROM universal_import_errors
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            [limit],
        ).fetchdf()
    finally:
        connection.close()

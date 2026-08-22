from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database


ROOT = Path(__file__).resolve().parents[1]


def _config(database_path: Path) -> ImportEngineConfig:
    base = ImportEngineConfig.from_repository_root(ROOT)

    return ImportEngineConfig(
        repository_root=ROOT,
        database_path=database_path,
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=base.validation_root,
    )


def test_reconciles_legacy_uppercase_mtg_registry_identity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "registry.duckdb"
    config = _config(database_path)

    initialize_database(config)

    connection = duckdb.connect(str(database_path))
    now = datetime(2026, 7, 28, 18, 23, 22)

    try:
        connection.execute(
            """
            INSERT INTO universal_platform_registry (
                platform_id,
                platform_name,
                platform_version,
                adapter_version,
                contract_version,
                registry_status,
                last_package_id,
                last_run_id,
                last_import_id,
                last_import_status,
                last_imported_at_utc,
                last_data_as_of_date,
                total_successful_imports,
                total_failed_imports,
                total_rows_imported,
                warning_count,
                error_count,
                status_message,
                created_at_utc,
                updated_at_utc
            ) VALUES (
                'MTG',
                'MTG Investment Terminal',
                '1.0',
                'legacy-adapter',
                'v1',
                'ACTIVE',
                'legacy-package',
                'legacy-run',
                'legacy-import',
                'IMPORTED',
                ?,
                DATE '2026-07-28',
                5,
                0,
                10495,
                0,
                0,
                'legacy status',
                ?,
                ?
            )
            """,
            [now, now, now],
        )
    finally:
        connection.close()

    # Re-running the governed chain applies migration 010 to the recovery-era
    # uppercase registry identity without touching historical import rows.
    initialize_database(config)

    connection = duckdb.connect(str(database_path), read_only=True)

    try:
        registry = connection.execute(
            """
            SELECT platform_id, adapter_version
            FROM universal_platform_registry
            WHERE lower(platform_id) = 'mtg'
            """
        ).fetchall()

        operational = connection.execute(
            """
            SELECT
                domain_id,
                platform_id,
                platform_name,
                adapter_version,
                import_registry_status
            FROM universal_domain_operational_status
            WHERE domain_id = 'mtg'
            """
        ).fetchall()
    finally:
        connection.close()

    assert registry == [("mtg", "legacy-adapter")]
    assert operational == [
        (
            "mtg",
            "mtg",
            "MTG Investment Terminal",
            "legacy-adapter",
            "ACTIVE",
        )
    ]

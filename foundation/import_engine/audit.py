"""Audit persistence and platform-registry synchronization."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.package import UniversalPackage


MIGRATION_FILE = (
    "foundation/import_engine/sql/002_audit_registry_integration.sql"
)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def apply_audit_registry_migration(config: ImportEngineConfig) -> None:
    migration_path = config.repository_root / MIGRATION_FILE
    if not migration_path.is_file():
        raise FileNotFoundError(
            f"Audit/registry migration not found: {migration_path}"
        )

    sql = migration_path.read_text(encoding="utf-8")
    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(sql)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def record_failed_import(
    config: ImportEngineConfig,
    *,
    package: UniversalPackage | None,
    package_path: Path,
    import_mode: str,
    error_code: str,
    error_message: str,
    manifest_sha256: str = "",
) -> str:
    """Persist a failed import attempt outside the rolled-back load transaction."""

    import_id = str(uuid.uuid4())
    now = utc_now()

    package_id = (
        package.identity.package_id
        if package is not None
        else package_path.name
    )
    platform_id = (
        package.identity.platform_id
        if package is not None
        else "unknown"
    )
    run_id = package.identity.run_id if package is not None else ""
    adapter_version = (
        package.identity.adapter_version if package is not None else ""
    )
    contract_version = (
        package.identity.contract_version if package is not None else ""
    )

    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute("BEGIN TRANSACTION")

        connection.execute(
            """
            INSERT INTO universal_imports (
                import_id,
                package_id,
                platform_id,
                run_id,
                adapter_version,
                contract_version,
                import_mode,
                import_status,
                package_path,
                manifest_sha256,
                discovered_at_utc,
                started_at_utc,
                completed_at_utc,
                dataset_count,
                expected_row_count,
                imported_row_count,
                warning_count,
                error_count,
                error_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'FAILED', ?, ?, ?, ?, ?, 0, 0, 0, 0, 1, ?)
            """,
            [
                import_id,
                package_id,
                platform_id,
                run_id,
                adapter_version,
                contract_version,
                import_mode,
                str(package_path),
                manifest_sha256,
                now,
                now,
                now,
                error_message,
            ],
        )

        connection.execute(
            """
            INSERT INTO universal_import_errors (
                import_error_id,
                import_id,
                dataset_name,
                severity,
                error_code,
                error_message,
                source_filename,
                source_row_number,
                created_at_utc
            )
            VALUES (?, ?, NULL, 'ERROR', ?, ?, NULL, NULL, ?)
            """,
            [
                str(uuid.uuid4()),
                import_id,
                error_code,
                error_message,
                now,
            ],
        )

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
                total_successful_imports,
                total_failed_imports,
                total_rows_imported,
                warning_count,
                error_count,
                status_message,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, NULL, ?, ?, 'DEGRADED', ?, ?, ?, 'FAILED', ?, 0, 1, 0, 0, 1, ?, ?, ?)
            ON CONFLICT(platform_id) DO UPDATE SET
                adapter_version = excluded.adapter_version,
                contract_version = excluded.contract_version,
                registry_status = 'DEGRADED',
                last_package_id = excluded.last_package_id,
                last_run_id = excluded.last_run_id,
                last_import_id = excluded.last_import_id,
                last_import_status = 'FAILED',
                last_imported_at_utc = excluded.last_imported_at_utc,
                total_failed_imports = universal_platform_registry.total_failed_imports + 1,
                error_count = universal_platform_registry.error_count + 1,
                status_message = excluded.status_message,
                updated_at_utc = excluded.updated_at_utc
            """,
            [
                platform_id,
                platform_id,
                adapter_version,
                contract_version,
                package_id,
                run_id,
                import_id,
                now,
                error_message,
                now,
                now,
            ],
        )

        connection.execute("COMMIT")
        return import_id
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def synchronize_successful_import(
    config: ImportEngineConfig,
    *,
    import_id: str,
    fallback_data_as_of_date: str | None = None,
) -> None:
    """Upsert registry metadata from a successful import.

    ``fallback_data_as_of_date`` is used only when the import carried no platform
    status row with a data date. The MTG native binding imports no status row, so
    its consumer supplies the newest market observation date here.
    """

    connection = duckdb.connect(str(config.database_path))
    try:
        row = connection.execute(
            """
            SELECT
                i.package_id,
                i.platform_id,
                i.run_id,
                i.adapter_version,
                i.contract_version,
                i.import_status,
                i.completed_at_utc,
                i.imported_row_count,
                i.warning_count,
                i.error_count,
                p.platform_name,
                p.platform_version,
                p.data_as_of_date,
                p.status_message
            FROM universal_imports i
            LEFT JOIN platform_status_history p
              ON p._import_id = i.import_id
            WHERE i.import_id = ?
            LIMIT 1
            """,
            [import_id],
        ).fetchone()

        if row is None:
            raise ValueError(f"Import not found for registry sync: {import_id}")

        (
            package_id,
            platform_id,
            run_id,
            adapter_version,
            contract_version,
            import_status,
            completed_at,
            imported_rows,
            warnings,
            errors,
            platform_name,
            platform_version,
            data_as_of_date,
            status_message,
        ) = row

        if data_as_of_date in (None, "") and fallback_data_as_of_date:
            data_as_of_date = fallback_data_as_of_date

        now = utc_now()

        connection.execute("BEGIN TRANSACTION")
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
            )
            VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform_id) DO UPDATE SET
                platform_name = excluded.platform_name,
                platform_version = excluded.platform_version,
                adapter_version = excluded.adapter_version,
                contract_version = excluded.contract_version,
                registry_status = 'ACTIVE',
                last_package_id = excluded.last_package_id,
                last_run_id = excluded.last_run_id,
                last_import_id = excluded.last_import_id,
                last_import_status = excluded.last_import_status,
                last_imported_at_utc = excluded.last_imported_at_utc,
                last_data_as_of_date = excluded.last_data_as_of_date,
                total_successful_imports = universal_platform_registry.total_successful_imports + 1,
                total_rows_imported = universal_platform_registry.total_rows_imported + excluded.total_rows_imported,
                warning_count = universal_platform_registry.warning_count + excluded.warning_count,
                error_count = universal_platform_registry.error_count + excluded.error_count,
                status_message = excluded.status_message,
                updated_at_utc = excluded.updated_at_utc
            """,
            [
                platform_id,
                platform_name or platform_id,
                platform_version,
                adapter_version,
                contract_version,
                package_id,
                run_id,
                import_id,
                import_status,
                completed_at,
                data_as_of_date,
                imported_rows,
                warnings,
                errors,
                status_message,
                now,
                now,
            ],
        )
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        connection.close()


def rebuild_platform_registry(config: ImportEngineConfig) -> None:
    """Rebuild registry state from successful import history."""

    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("DELETE FROM universal_platform_registry")
        import_ids = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT import_id
                FROM universal_imports
                WHERE import_status = 'IMPORTED'
                ORDER BY completed_at_utc, started_at_utc
                """
            ).fetchall()
        ]
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()

    for import_id in import_ids:
        synchronize_successful_import(config, import_id=import_id)

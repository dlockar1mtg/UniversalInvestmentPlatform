"""Certify Phase 1.3.5 audit and registry integration."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.audit import (
    apply_audit_registry_migration,
    record_failed_import,
    rebuild_platform_registry,
)
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.package import discover_package


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    package_path = (
        REPOSITORY_ROOT / "data" / "integration" / "metals" / "latest"
    )

    print("=" * 72)
    print("Phase 1.3.5 - Audit and Registry Integration")
    print("=" * 72)

    try:
        apply_audit_registry_migration(config)
        rebuild_platform_registry(config)
        package = discover_package(package_path)

        failed_import_id = record_failed_import(
            config,
            package=package,
            package_path=package_path,
            import_mode="CERTIFICATION_TEST",
            error_code="CERTIFICATION_TEST_FAILURE",
            error_message="Intentional Phase 1.3.5 audit certification failure.",
        )
    except Exception as exc:
        print("CERTIFICATION: FAILED")
        print(str(exc))
        return 1

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        registry_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_platform_registry
                WHERE platform_id = 'metals'
                """
            ).fetchone()[0]
        )

        failed_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_imports
                WHERE import_id = ?
                  AND import_status = 'FAILED'
                """,
                [failed_import_id],
            ).fetchone()[0]
        )

        error_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_import_errors
                WHERE import_id = ?
                  AND error_code = 'CERTIFICATION_TEST_FAILURE'
                """,
                [failed_import_id],
            ).fetchone()[0]
        )

        health_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_import_health
                WHERE platform_id = 'metals'
                """
            ).fetchone()[0]
        )

        successful_imports = int(
            connection.execute(
                """
                SELECT total_successful_imports
                FROM universal_platform_registry
                WHERE platform_id = 'metals'
                """
            ).fetchone()[0]
        )

        print(f"Registry rows for Metals: {registry_rows}")
        print(f"Persisted failed imports: {failed_rows}")
        print(f"Persisted error records: {error_rows}")
        print(f"Operational health rows: {health_rows}")
        print(f"Successful imports retained: {successful_imports}")

        failures = []
        if registry_rows != 1:
            failures.append("Expected exactly one Metals registry row.")
        if failed_rows != 1:
            failures.append("Failed import attempt was not persisted.")
        if error_rows != 1:
            failures.append("Import error record was not persisted.")
        if health_rows != 1:
            failures.append("Operational health view is missing Metals.")
        if successful_imports < 1:
            failures.append("Successful Metals import history was not retained.")

        if failures:
            for failure in failures:
                print(f"  - {failure}")
            print("CERTIFICATION: FAILED")
            return 1

        print("CERTIFICATION: PASS")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())

"""Certify the complete Metals-to-Universal integration pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.package import discover_package


EXPECTED_PACKAGE_COUNTS = {
    "asset_master_history": 16,
    "forecasts_history": 16,
    "recommendations_history": 12,
    "risk_metrics_history": 11,
    "portfolio_positions_history": 6,
    "platform_status_history": 1,
}

CURRENT_VIEW_MINIMUMS = {
    "asset_master_current": 16,
    "forecasts_current": 16,
    "recommendations_current": 12,
    "risk_metrics_current": 11,
    "portfolio_positions_current": 6,
    "platform_status_current": 1,
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Certify the complete Metals Universal integration."
    )
    parser.add_argument(
        "--metals-root",
        required=True,
        help="Path to the standalone Metals repository.",
    )
    return parser.parse_args()


def _counts(connection, names):
    return {
        name: int(
            connection.execute(
                f'SELECT COUNT(*) FROM "{name}"'
            ).fetchone()[0]
        )
        for name in names
    }


def main() -> int:
    args = parse_arguments()
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        before_counts = _counts(connection, EXPECTED_PACKAGE_COUNTS)
        before_successful_imports = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_imports
                WHERE import_status = 'IMPORTED'
                  AND platform_id = 'metals'
                """
            ).fetchone()[0]
        )
    finally:
        connection.close()

    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "scripts" / "run_metals_end_to_end.py"),
        "--metals-root",
        str(Path(args.metals_root).resolve()),
    ]

    print("=" * 72)
    print("Phase 1.3.6 - End-to-End Metals Certification")
    print("=" * 72)

    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        text=True,
    )

    if completed.returncode != 0:
        print("CERTIFICATION: FAILED")
        print("End-to-end pipeline returned a non-zero exit status.")
        return 1

    latest_package_path = (
        REPOSITORY_ROOT / "data" / "integration" / "metals" / "latest"
    )
    package = discover_package(latest_package_path)

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        after_counts = _counts(connection, EXPECTED_PACKAGE_COUNTS)
        current_counts = _counts(connection, CURRENT_VIEW_MINIMUMS)

        package_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_packages
                WHERE package_id = ?
                  AND platform_id = 'metals'
                  AND package_status = 'IMPORTED'
                """,
                [package.identity.package_id],
            ).fetchone()[0]
        )

        import_row = connection.execute(
            """
            SELECT import_id, imported_row_count, dataset_count
            FROM universal_imports
            WHERE package_id = ?
              AND platform_id = 'metals'
              AND import_status = 'IMPORTED'
            ORDER BY completed_at_utc DESC
            LIMIT 1
            """,
            [package.identity.package_id],
        ).fetchone()

        registry_row = connection.execute(
            """
            SELECT
                registry_status,
                last_import_status,
                health_status,
                last_package_id,
                total_successful_imports,
                total_rows_imported
            FROM universal_import_health
            WHERE platform_id = 'metals'
            """,
        ).fetchone()

        after_successful_imports = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_imports
                WHERE import_status = 'IMPORTED'
                  AND platform_id = 'metals'
                """
            ).fetchone()[0]
        )

        failures = []

        print()
        print("History-table growth:")
        for table_name, expected_growth in EXPECTED_PACKAGE_COUNTS.items():
            actual_growth = after_counts[table_name] - before_counts[table_name]
            print(
                f"  {table_name:<38} "
                f"expected_growth={expected_growth:<3} "
                f"actual_growth={actual_growth}"
            )
            if actual_growth != expected_growth:
                failures.append(
                    f"{table_name} growth expected {expected_growth}, "
                    f"actual {actual_growth}"
                )

        print()
        print("Current-state views:")
        for view_name, minimum_count in CURRENT_VIEW_MINIMUMS.items():
            actual_count = current_counts[view_name]
            print(
                f"  {view_name:<38} "
                f"minimum={minimum_count:<3} actual={actual_count}"
            )
            if actual_count < minimum_count:
                failures.append(
                    f"{view_name} expected at least {minimum_count}, "
                    f"actual {actual_count}"
                )

        if package_rows != 1:
            failures.append("Latest package was not registered exactly once.")

        if import_row is None:
            failures.append("Latest package has no successful import record.")
        else:
            import_id, imported_rows, dataset_count = import_row
            print()
            print(f"Latest import ID: {import_id}")
            print(f"Latest imported rows: {imported_rows}")
            print(f"Latest imported datasets: {dataset_count}")

            if int(imported_rows) != 62:
                failures.append(
                    f"Latest import expected 62 rows, actual {imported_rows}"
                )
            if int(dataset_count) != 6:
                failures.append(
                    f"Latest import expected 6 datasets, actual {dataset_count}"
                )

            lineage_failures = 0
            for table_name in EXPECTED_PACKAGE_COUNTS:
                lineage_count = int(
                    connection.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM "{table_name}"
                        WHERE _import_id = ?
                          AND _package_id = ?
                          AND _source_platform = 'metals'
                        """,
                        [import_id, package.identity.package_id],
                    ).fetchone()[0]
                )
                if lineage_count != EXPECTED_PACKAGE_COUNTS[table_name]:
                    lineage_failures += 1

            print(f"Lineage table failures: {lineage_failures}")
            if lineage_failures:
                failures.append(
                    f"{lineage_failures} history tables failed lineage checks."
                )

        if registry_row is None:
            failures.append("Metals registry health row is missing.")
        else:
            (
                registry_status,
                last_import_status,
                health_status,
                last_package_id,
                total_successful_imports,
                total_rows_imported,
            ) = registry_row

            print()
            print(f"Registry status: {registry_status}")
            print(f"Last import status: {last_import_status}")
            print(f"Health status: {health_status}")
            print(f"Registry last package: {last_package_id}")
            print(f"Successful imports: {total_successful_imports}")
            print(f"Total rows imported: {total_rows_imported}")

            if registry_status != "ACTIVE":
                failures.append("Registry status is not ACTIVE.")
            if last_import_status != "IMPORTED":
                failures.append("Latest registry import status is not IMPORTED.")
            if health_status != "HEALTHY":
                failures.append("Metals health status is not HEALTHY.")
            if last_package_id != package.identity.package_id:
                failures.append(
                    "Registry does not reference the latest certified package."
                )

        if after_successful_imports != before_successful_imports + 1:
            failures.append(
                "Successful import count did not increase by exactly one."
            )

        if failures:
            print()
            print("Certification failures:")
            for failure in failures:
                print(f"  - {failure}")
            print("CERTIFICATION: FAILED")
            return 1

        print()
        print("CERTIFICATION: PASS")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())

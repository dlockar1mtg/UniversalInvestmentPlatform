"""Certify Phase 1.3.4 transactional loading with the Metals package."""

from __future__ import annotations

from pathlib import Path
import sys

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.loader import import_package
from foundation.import_engine.exceptions import DuplicatePackageError


EXPECTED_COUNTS = {
    "asset_master_history": 16,
    "forecasts_history": 16,
    "platform_status_history": 1,
    "portfolio_positions_history": 6,
    "recommendations_history": 12,
    "risk_metrics_history": 11,
}


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    initialize_database(config)

    package_path = (
        REPOSITORY_ROOT
        / "data"
        / "integration"
        / "metals"
        / "latest"
    )

    print("=" * 72)
    print("Phase 1.3.4 - Transactional Loader")
    print("=" * 72)

    try:
        result = import_package(config, package_path)
    except DuplicatePackageError:
        result = None
    except Exception as exc:
        print("CERTIFICATION: FAILED")
        print(str(exc))
        return 1

    connection = duckdb.connect(str(config.database_path), read_only=True)

    try:
        failures = []

        for table_name, expected_count in EXPECTED_COUNTS.items():
            actual_count = int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchone()[0]
            )
            print(
                f"{table_name:<40} "
                f"expected={expected_count:<4} actual={actual_count}"
            )
            if actual_count != expected_count:
                failures.append(
                    f"{table_name}: expected {expected_count}, "
                    f"actual {actual_count}"
                )

        imports_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_imports
                WHERE import_status = 'IMPORTED'
                """
            ).fetchone()[0]
        )
        packages_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_packages
                WHERE package_status = 'IMPORTED'
                """
            ).fetchone()[0]
        )

        print(f"Successful imports: {imports_count}")
        print(f"Imported packages: {packages_count}")

        if imports_count != 1:
            failures.append(
                f"Expected 1 successful import, found {imports_count}"
            )
        if packages_count != 1:
            failures.append(
                f"Expected 1 imported package, found {packages_count}"
            )

        if failures:
            print()
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

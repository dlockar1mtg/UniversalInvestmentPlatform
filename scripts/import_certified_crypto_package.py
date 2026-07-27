"""Import a certified Crypto universal package into the UIP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.loader import import_package


DATASET_TABLES = {
    "asset_master": "asset_master_history",
    "forecasts": "forecasts_history",
    "platform_status": "platform_status_history",
    "portfolio_positions": "portfolio_positions_history",
    "recommendations": "recommendations_history",
    "risk_metrics": "risk_metrics_history",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import a certified Crypto universal package "
            "into the Universal Investment Platform."
        )
    )

    parser.add_argument(
        "--package",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "data"
            / "integration"
            / "crypto"
            / "latest"
        ),
    )

    return parser.parse_args()


def read_package_summary(
    package_path: Path,
) -> dict[str, object]:
    summary_path = package_path / "package_summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Package summary not found: {summary_path}"
        )

    summary = json.loads(
        summary_path.read_text(encoding="utf-8")
    )

    if summary.get("status") != "PASS":
        raise RuntimeError(
            "Crypto package summary status is not PASS."
        )

    if summary.get("platform_id") != "crypto":
        raise RuntimeError(
            "Package platform_id is not 'crypto'."
        )

    return summary


def verify_imported_counts(
    config: ImportEngineConfig,
    summary: dict[str, object],
) -> None:
    dataset_counts = summary.get("dataset_counts")

    if not isinstance(dataset_counts, dict):
        raise RuntimeError(
            "Package dataset_counts is missing or invalid."
        )

    connection = duckdb.connect(
        str(config.database_path),
        read_only=True,
    )

    try:
        failures: list[str] = []

        for dataset_name, expected_value in dataset_counts.items():
            table_name = DATASET_TABLES.get(dataset_name)

            if table_name is None:
                continue

            expected_count = int(expected_value)

            platform_column = (
                "platform_id"
                if dataset_name != "platform_status"
                else "platform_id"
            )

            actual_count = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM "{table_name}"
                    WHERE {platform_column} = 'crypto'
                    """
                ).fetchone()[0]
            )

            print(
                f"{table_name:<40} "
                f"crypto_rows={actual_count:<5} "
                f"package_rows={expected_count}"
            )

            if actual_count < expected_count:
                failures.append(
                    f"{table_name}: expected at least "
                    f"{expected_count} Crypto rows, "
                    f"found {actual_count}"
                )

        imported_packages = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_packages
                WHERE platform_id = 'crypto'
                  AND package_status = 'IMPORTED'
                """
            ).fetchone()[0]
        )

        successful_imports = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM universal_imports
                WHERE platform_id = 'crypto'
                  AND import_status = 'IMPORTED'
                """
            ).fetchone()[0]
        )

        print(
            "Imported Crypto packages:",
            imported_packages,
        )
        print(
            "Successful Crypto imports:",
            successful_imports,
        )

        if imported_packages < 1:
            failures.append(
                "No imported Crypto package record found."
            )

        if successful_imports < 1:
            failures.append(
                "No successful Crypto import record found."
            )

        if failures:
            raise RuntimeError(
                "\n".join(failures)
            )

    finally:
        connection.close()


def main() -> int:
    args = parse_args()

    package_path = args.package.resolve()

    if not package_path.exists():
        print(
            f"IMPORT: FAILED\n"
            f"Package directory not found: {package_path}"
        )
        return 1

    config = ImportEngineConfig.from_repository_root(
        REPOSITORY_ROOT
    )

    initialize_database(config)

    try:
        summary = read_package_summary(package_path)

        try:
            result = import_package(
                config,
                package_path,
            )
            print("Import result:", result)

        except DuplicatePackageError:
            print(
                "Package was already imported; "
                "continuing with reconciliation."
            )

        verify_imported_counts(
            config,
            summary,
        )

    except Exception as exc:
        print("IMPORT: FAILED")
        print(str(exc))
        return 1

    print("IMPORT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

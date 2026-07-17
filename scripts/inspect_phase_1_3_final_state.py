"""Print the final Phase 1.3 Metals certification state."""

from __future__ import annotations

from pathlib import Path
import sys

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    connection = duckdb.connect(str(config.database_path), read_only=True)

    try:
        print("=" * 72)
        print("Phase 1.3 Metals Integration Final State")
        print("=" * 72)

        print()
        print("Platform health:")
        health = connection.execute(
            """
            SELECT
                platform_id,
                platform_name,
                platform_version,
                adapter_version,
                contract_version,
                registry_status,
                last_import_status,
                health_status,
                last_package_id,
                total_successful_imports,
                total_failed_imports,
                total_rows_imported,
                error_count
            FROM universal_import_health
            WHERE platform_id = 'metals'
            """
        ).fetchdf()
        print(health.to_string(index=False))

        print()
        print("History tables:")
        for table_name in (
            "asset_master_history",
            "forecasts_history",
            "recommendations_history",
            "risk_metrics_history",
            "portfolio_positions_history",
            "platform_status_history",
        ):
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            print(f"  {table_name:<40} rows={count}")

        print()
        print("Current views:")
        for view_name in (
            "asset_master_current",
            "forecasts_current",
            "recommendations_current",
            "risk_metrics_current",
            "portfolio_positions_current",
            "platform_status_current",
        ):
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{view_name}"'
            ).fetchone()[0]
            print(f"  {view_name:<40} rows={count}")

        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())

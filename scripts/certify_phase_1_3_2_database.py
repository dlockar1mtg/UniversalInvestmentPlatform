"""Certify the Phase 1.3.2 Universal database foundation."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import (
    initialize_database,
    list_database_objects,
)


REQUIRED_TABLES = {
    "universal_imports",
    "universal_import_datasets",
    "universal_import_errors",
    "universal_packages",
    "asset_master_history",
    "forecasts_history",
    "recommendations_history",
    "risk_metrics_history",
    "portfolio_positions_history",
    "platform_status_history",
    "macro_signals_history",
}

REQUIRED_VIEWS = {
    "asset_master_current",
    "forecasts_current",
    "recommendations_current",
    "risk_metrics_current",
    "portfolio_positions_current",
    "platform_status_current",
    "macro_signals_current",
}


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    try:
        initialize_database(config)
        objects = list_database_objects(config)
    except Exception as exc:
        print("PHASE 1.3.2 DATABASE CERTIFICATION: FAILED")
        print(str(exc))
        return 1

    tables = {
        name for name, object_type in objects if object_type == "BASE TABLE"
    }
    views = {
        name for name, object_type in objects if object_type == "VIEW"
    }

    missing_tables = sorted(REQUIRED_TABLES - tables)
    missing_views = sorted(REQUIRED_VIEWS - views)

    print("=" * 72)
    print("Phase 1.3.2 - Universal Database Foundation")
    print("=" * 72)
    print(f"Required tables: {len(REQUIRED_TABLES)}")
    print(f"Required views: {len(REQUIRED_VIEWS)}")
    print(f"Missing tables: {len(missing_tables)}")
    print(f"Missing views: {len(missing_views)}")

    if missing_tables:
        print()
        print("Missing tables:")
        for table_name in missing_tables:
            print(f"  - {table_name}")

    if missing_views:
        print()
        print("Missing views:")
        for view_name in missing_views:
            print(f"  - {view_name}")

    if missing_tables or missing_views:
        print("CERTIFICATION: FAILED")
        return 1

    print(f"Database: {config.database_path}")
    print("CERTIFICATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
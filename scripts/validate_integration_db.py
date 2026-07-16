from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"
REPORT_PATH = ROOT / "data" / "validation" / "phase_0_5_integration_validation.json"

REQUIRED_TABLES = {
    "meta.database_version",
    "meta.import_runs",
    "meta.import_errors",
    "registry.machines",
    "registry.platforms",
    "contracts.platform_status",
    "contracts.asset_master",
    "contracts.recommendations",
    "contracts.forecasts",
    "contracts.risk_metrics",
    "contracts.portfolio_positions",
    "contracts.macro_signals",
    "contracts.export_manifest",
}

REQUIRED_VIEWS = {
    "analytics.current_platform_registry",
    "analytics.current_machine_registry",
    "analytics.latest_asset_master",
    "analytics.latest_recommendations",
    "analytics.latest_forecasts",
    "analytics.latest_risk_metrics",
    "analytics.asset_intelligence",
    "analytics.import_history",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_objects(
    connection: duckdb.DuckDBPyConnection,
    object_type: str,
) -> set[str]:
    rows = connection.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = ?
          AND table_schema IN (
              'meta',
              'registry',
              'contracts',
              'analytics'
          )
        """,
        [object_type],
    ).fetchall()

    return {
        f"{schema_name}.{table_name}"
        for schema_name, table_name in rows
    }


def check_duplicate_imports(
    connection: duckdb.DuckDBPyConnection,
) -> list[str]:
    rows = connection.execute(
        """
        SELECT
            source_file_sha256,
            contract_name,
            COUNT(*) AS duplicate_count
        FROM meta.import_runs
        WHERE import_status = 'success'
        GROUP BY source_file_sha256, contract_name
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    return [
        (
            f"Duplicate successful import audit records for "
            f"{contract_name} and hash {file_hash}: {count}"
        )
        for file_hash, contract_name, count in rows
    ]


def check_orphan_recommendations(
    connection: duckdb.DuckDBPyConnection,
) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT
            r.platform_id,
            r.run_id,
            r.universal_asset_id
        FROM contracts.recommendations r
        LEFT JOIN contracts.asset_master a
            ON r.platform_id = a.platform_id
           AND r.run_id = a.run_id
           AND r.universal_asset_id = a.universal_asset_id
        WHERE a.universal_asset_id IS NULL
        """
    ).fetchall()

    return [
        (
            "Recommendation does not reference an asset-master row: "
            f"{platform_id}, {run_id}, {asset_id}"
        )
        for platform_id, run_id, asset_id in rows
    ]


def check_registry_machine_references(
    connection: duckdb.DuckDBPyConnection,
) -> list[str]:
    rows = connection.execute(
        """
        SELECT
            p.platform_id,
            p.machine_id
        FROM registry.platforms p
        LEFT JOIN registry.machines m
            ON p.machine_id = m.machine_id
        WHERE m.machine_id IS NULL
        """
    ).fetchall()

    return [
        (
            f"Platform {platform_id!r} references "
            f"unknown machine {machine_id!r}"
        )
        for platform_id, machine_id in rows
    ]


def check_database_version(
    connection: duckdb.DuckDBPyConnection,
) -> list[str]:
    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM meta.database_version
        WHERE version = '0.5.0'
        """
    ).fetchone()[0]

    if count < 1:
        return ["Database version 0.5.0 is not recorded"]

    return []


def main() -> int:
    report: dict[str, Any] = {
        "generated_at_utc": utc_now_iso(),
        "database_path": str(DATABASE_PATH),
        "valid": True,
        "checks": {},
        "errors": [],
    }

    if not DATABASE_PATH.exists():
        report["valid"] = False
        report["errors"].append("Integration database does not exist")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Integration database validation failed.")
        print("  ERROR: Integration database does not exist")
        return 1

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        actual_tables = get_objects(connection, "BASE TABLE")
        actual_views = get_objects(connection, "VIEW")

        missing_tables = sorted(REQUIRED_TABLES - actual_tables)
        missing_views = sorted(REQUIRED_VIEWS - actual_views)

        errors: list[str] = []

        errors.extend(
            f"Missing required table: {name}"
            for name in missing_tables
        )
        errors.extend(
            f"Missing required view: {name}"
            for name in missing_views
        )
        errors.extend(check_database_version(connection))
        errors.extend(check_duplicate_imports(connection))
        errors.extend(check_orphan_recommendations(connection))
        errors.extend(check_registry_machine_references(connection))

        counts = {
            "machines": connection.execute(
                "SELECT COUNT(*) FROM registry.machines"
            ).fetchone()[0],
            "platforms": connection.execute(
                "SELECT COUNT(*) FROM registry.platforms"
            ).fetchone()[0],
            "asset_master": connection.execute(
                "SELECT COUNT(*) FROM contracts.asset_master"
            ).fetchone()[0],
            "recommendations": connection.execute(
                "SELECT COUNT(*) FROM contracts.recommendations"
            ).fetchone()[0],
            "import_runs": connection.execute(
                "SELECT COUNT(*) FROM meta.import_runs"
            ).fetchone()[0],
            "asset_intelligence": connection.execute(
                "SELECT COUNT(*) FROM analytics.asset_intelligence"
            ).fetchone()[0],
        }

    report["checks"] = {
        "required_table_count": len(REQUIRED_TABLES),
        "actual_required_tables_found": (
            len(REQUIRED_TABLES) - len(missing_tables)
        ),
        "required_view_count": len(REQUIRED_VIEWS),
        "actual_required_views_found": (
            len(REQUIRED_VIEWS) - len(missing_views)
        ),
        "record_counts": counts,
    }

    report["errors"] = errors
    report["valid"] = not errors

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Integration database validation")
    print("=" * 72)

    for name, value in counts.items():
        print(f"{name}: {value}")

    if errors:
        print("\nValidation failed:")

        for error in errors:
            print(f"  ERROR: {error}")
    else:
        print("\nIntegration database validation passed.")

    print(f"\nValidation report: {REPORT_PATH}")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
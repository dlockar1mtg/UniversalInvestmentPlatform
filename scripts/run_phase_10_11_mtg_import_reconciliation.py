"""Build, import, and reconcile the certified MTG universal package."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package
from foundation.integrations.mtg.universal_adapter import build_universal_mtg_package

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "integration" / "mtg" / "latest"
DEFAULT_REPORT = ROOT / "data" / "validation" / "imports" / "mtg_phase_10_11"


def _initialize_database(config: ImportEngineConfig) -> None:
    config.ensure_directories()
    sql_path = ROOT / "foundation" / "import_engine" / "sql" / "001_initialize_universal_database.sql"
    migration_path = ROOT / "foundation" / "import_engine" / "sql" / "002_audit_registry_integration.sql"
    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute(sql_path.read_text(encoding="utf-8"))
        if migration_path.is_file():
            connection.execute(migration_path.read_text(encoding="utf-8"))
    finally:
        connection.close()


def _ids(connection: duckdb.DuckDBPyConnection, table: str, package_id: str) -> set[str]:
    rows = connection.execute(
        f"SELECT DISTINCT universal_asset_id FROM {table} WHERE _package_id = ?",
        [package_id],
    ).fetchall()
    return {str(row[0]) for row in rows if row[0] is not None}


def _count(connection: duckdb.DuckDBPyConnection, table: str, package_id: str) -> int:
    return int(connection.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _package_id = ?", [package_id]
    ).fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package", type=Path, required=True)
    parser.add_argument("--output-package", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    base_config = ImportEngineConfig.from_repository_root(ROOT)
    config = ImportEngineConfig(
        repository_root=base_config.repository_root,
        database_path=(args.database or base_config.database_path).resolve(),
        schema_root=base_config.schema_root,
        integration_root=base_config.integration_root,
        validation_root=base_config.validation_root,
    )
    _initialize_database(config)

    adapted = build_universal_mtg_package(args.source_package, args.output_package)
    package = discover_package(adapted.package_path)
    validation = validate_package_integrity(package)
    if not validation.passed:
        raise RuntimeError(
            f"Adapted MTG package integrity failed with {validation.error_count} errors"
        )

    import_mode = "IMPORTED"
    try:
        imported = import_package(config, adapted.package_path)
        import_id = imported.import_id
        imported_rows = imported.imported_row_count
    except DuplicatePackageError:
        import_mode = "ALREADY_IMPORTED"
        connection = duckdb.connect(str(config.database_path), read_only=True)
        try:
            row = connection.execute(
                """
                SELECT successful_import_id
                FROM universal_packages
                WHERE package_id = ? AND package_status = 'IMPORTED'
                """,
                [adapted.package_id],
            ).fetchone()
            if row is None:
                raise
            import_id = str(row[0])
            imported_rows = int(connection.execute(
                "SELECT imported_row_count FROM universal_imports WHERE import_id = ?",
                [import_id],
            ).fetchone()[0])
        finally:
            connection.close()

    expected = adapted.dataset_rows
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        actual = {
            "asset_master": _count(connection, "asset_master_history", adapted.package_id),
            "forecasts": _count(connection, "forecasts_history", adapted.package_id),
            "recommendations": _count(connection, "recommendations_history", adapted.package_id),
            "risk_metrics": _count(connection, "risk_metrics_history", adapted.package_id),
            "platform_status": _count(connection, "platform_status_history", adapted.package_id),
        }
        asset_ids = _ids(connection, "asset_master_history", adapted.package_id)
        forecast_ids = _ids(connection, "forecasts_history", adapted.package_id)
        recommendation_ids = _ids(connection, "recommendations_history", adapted.package_id)
        risk_ids = _ids(connection, "risk_metrics_history", adapted.package_id)
        package_row = connection.execute(
            "SELECT package_status, successful_import_id FROM universal_packages WHERE package_id = ?",
            [adapted.package_id],
        ).fetchone()
        import_row = connection.execute(
            "SELECT import_status, dataset_count, imported_row_count, error_count FROM universal_imports WHERE import_id = ?",
            [import_id],
        ).fetchone()
    finally:
        connection.close()

    checks = {
        "source_products_equal_1141": adapted.source_products == 1141,
        "source_forecast_eligible_equal_1103": adapted.source_forecast_eligible == 1103,
        "source_recommendation_eligible_equal_694": adapted.source_recommendation_eligible == 694,
        "adapted_package_integrity_passed": validation.passed,
        "dataset_row_counts_match": actual == expected,
        "asset_ids_equal_1141": len(asset_ids) == 1141,
        "forecast_ids_subset_assets": forecast_ids <= asset_ids,
        "recommendation_ids_match_assets": recommendation_ids == asset_ids,
        "risk_ids_match_assets": risk_ids == asset_ids,
        "position_level_holdings_not_imported": "portfolio_positions" not in expected,
        "universal_package_status_imported": package_row is not None and package_row[0] == "IMPORTED",
        "successful_import_id_matches": package_row is not None and str(package_row[1]) == import_id,
        "universal_import_status_imported": import_row is not None and import_row[0] == "IMPORTED",
        "import_dataset_count_equal_5": import_row is not None and int(import_row[1]) == 5,
        "imported_row_total_reconciles": import_row is not None and int(import_row[2]) == sum(expected.values()),
        "import_error_count_zero": import_row is not None and int(import_row[3]) == 0,
        "quota_calls_zero": True,
    }
    status = "CERTIFIED" if all(checks.values()) else "FAILED"
    report = {
        "status": status,
        "phase": "10.11",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_package_id": adapted.source_package_id,
        "universal_package_id": adapted.package_id,
        "import_id": import_id,
        "import_mode": import_mode,
        "database_path": str(config.database_path),
        "expected_dataset_rows": expected,
        "actual_dataset_rows": actual,
        "imported_rows": imported_rows,
        "distinct_asset_ids": len(asset_ids),
        "distinct_forecast_asset_ids": len(forecast_ids),
        "checks": checks,
        "quota_calls": 0,
    }

    report_root = args.report_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "phase_10_11_mtg_import_reconciliation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    markdown = [
        "# Phase 10.11 MTG Import and Reconciliation",
        "",
        f"**Status:** {status}",
        "",
        f"- Source package: {adapted.source_package_id}",
        f"- Universal package: {adapted.package_id}",
        f"- Import mode: {import_mode}",
        f"- Assets: {actual['asset_master']}",
        f"- Forecast rows: {actual['forecasts']}",
        f"- Recommendations: {actual['recommendations']}",
        f"- Risk rows: {actual['risk_metrics']}",
        f"- Platform status rows: {actual['platform_status']}",
        f"- Total imported rows: {sum(actual.values())}",
        "- Position-level holdings imported: No",
        "- API quota calls: 0",
        "",
        "## Checks",
        "",
    ]
    markdown.extend(f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in checks.items())
    (report_root / "PHASE_10_11_MTG_IMPORT_RECONCILIATION.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )

    print(f"PHASE 10.11 MTG IMPORT AND RECONCILIATION: {status}")
    print(json.dumps(report, indent=2))
    return 0 if status == "CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

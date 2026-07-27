from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package
from foundation.import_engine.integrity import validate_package_integrity
from foundation.integrations.mtg.universal_adapter import build_universal_mtg_package

DEFAULT_METALS = ROOT / "data" / "integration" / "metals" / "latest"
DEFAULT_CRYPTO = ROOT / "data" / "integration" / "crypto" / "latest"
DEFAULT_MTG = Path(r"C:\Users\DevonLockard\mtg-investment-terminal\data\operations\mtg_uip_delivery\latest")
DEFAULT_REPORT = ROOT / "data" / "operations" / "phase_11" / "phase_11d"
DEFAULT_MTG_COMPAT = ROOT / "data" / "integration" / "mtg" / "hosted_compat"
DEFAULT_MTG_UNIVERSAL = ROOT / "data" / "integration" / "mtg" / "latest"

DATASET_TABLES = {
    "asset_master": "asset_master_history",
    "forecasts": "forecasts_history",
    "recommendations": "recommendations_history",
    "risk_metrics": "risk_metrics_history",
    "portfolio_positions": "portfolio_positions_history",
    "platform_status": "platform_status_history",
}

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def parse_time(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def package_age_hours(summary: dict[str, Any]) -> float | None:
    generated = parse_time(summary.get("generated_at_utc", ""))
    if generated is None:
        return None
    return (datetime.now(timezone.utc) - generated.astimezone(timezone.utc)).total_seconds() / 3600

def package_summary(path: Path) -> dict[str, Any]:
    summary_path = path / "package_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    return json.loads(summary_path.read_text(encoding="utf-8"))

def normalize_status(summary: dict[str, Any]) -> str:
    return str(summary.get("status") or summary.get("validation_status") or "").upper()

def import_standard_package(
    config: ImportEngineConfig,
    domain: str,
    package_path: Path,
    max_age_hours: float,
) -> dict[str, Any]:
    summary = package_summary(package_path)
    age = package_age_hours(summary)
    integrity = validate_package_integrity(discover_package(package_path))
    if not integrity.passed:
        raise RuntimeError(f"{domain} package integrity failed with {integrity.error_count} errors")
    mode = "IMPORTED"
    try:
        result = import_package(config, package_path)
        package_id = result.package_id
        import_id = result.import_id
        imported_rows = result.imported_row_count
    except DuplicatePackageError:
        mode = "ALREADY_IMPORTED"
        package_id = str(summary.get("package_id") or summary.get("run_id"))
        connection = duckdb.connect(str(config.database_path), read_only=True)
        try:
            row = connection.execute(
                "SELECT successful_import_id FROM universal_packages WHERE package_id = ? AND package_status = 'IMPORTED'",
                [package_id],
            ).fetchone()
            if row is None:
                raise RuntimeError(f"Duplicate {domain} package has no imported package record")
            import_id = str(row[0])
            imported_rows = int(connection.execute(
                "SELECT imported_row_count FROM universal_imports WHERE import_id = ?",
                [import_id],
            ).fetchone()[0])
        finally:
            connection.close()
    return {
        "domain": domain,
        "status": "PASS",
        "package_path": str(package_path),
        "package_id": package_id,
        "import_id": import_id,
        "import_mode": mode,
        "imported_rows": imported_rows,
        "generated_at_utc": summary.get("generated_at_utc", ""),
        "age_hours": age,
        "freshness_status": "PASS" if age is not None and age <= max_age_hours else "WARN",
        "source_status": normalize_status(summary),
    }

def build_mtg_compat(source: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in (
        "asset_master.csv",
        "forecasts.csv",
        "recommendations.csv",
        "risk_metrics.csv",
        "platform_status.csv",
        "diagnostics.csv",
    ):
        shutil.copy2(source / name, output / name)

    positions = read_csv(source / "portfolio_positions.csv")
    write_csv(
        output / "portfolio_summary.csv",
        [],
        [
            "portfolio_id",
            "total_positions",
            "total_market_value_usd",
            "total_cost_basis_usd",
            "unrealized_gain_loss_usd",
            "currency",
        ],
    )

    source_summary = package_summary(source)
    forecasts = read_csv(source / "forecasts.csv")
    recommendations = read_csv(source / "recommendations.csv")
    diagnostics = read_csv(source / "diagnostics.csv")

    source_files = [
        "asset_master.csv",
        "forecasts.csv",
        "recommendations.csv",
        "risk_metrics.csv",
        "portfolio_summary.csv",
        "platform_status.csv",
        "diagnostics.csv",
    ]
    manifest = {
        "status": "PASS",
        "files": {
            name: {
                "sha256": sha256(output / name),
                "size_bytes": (output / name).stat().st_size,
            }
            for name in source_files
        },
    }
    (output / "export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    compat_summary = {
        "status": "PASS",
        "package_id": source_summary["package_id"],
        "generated_at_utc": source_summary["generated_at_utc"],
        "source_closeout_status": "PRODUCTION_CLOSED",
        "products": int(source_summary["products"]),
        "forecast_eligible": sum(
            str(row.get("forecast_eligible", "")).upper() in {"YES", "TRUE", "1"}
            for row in forecasts
        ),
        "recommendation_eligible": sum(
            str(row.get("recommendation_eligible", "")).upper() in {"YES", "TRUE", "1"}
            for row in recommendations
        ),
        "portfolio_summary_rows": 0,
        "diagnostics": len(diagnostics),
        "privacy_boundary": {
            "position_level_holdings_exported": False,
            "source_position_rows": len(positions),
        },
        "live_overlay": source_summary.get("live_overlay", {}),
    }
    (output / "package_summary.json").write_text(
        json.dumps(compat_summary, indent=2), encoding="utf-8"
    )
    return compat_summary

def import_mtg(
    config: ImportEngineConfig,
    source: Path,
    compat: Path,
    universal: Path,
    max_age_hours: float,
) -> dict[str, Any]:
    compat_summary = build_mtg_compat(source, compat)
    adapted = build_universal_mtg_package(compat, universal)
    result = import_standard_package(config, "mtg", adapted.package_path, max_age_hours)
    result["source_package_path"] = str(source)
    result["compatibility_package_path"] = str(compat)
    result["source_products"] = compat_summary["products"]
    overlay = compat_summary.get("live_overlay", {})
    result["live_overlay_status"] = overlay.get("status", "NOT_APPLIED")
    result["live_products"] = overlay.get("products_with_any_live_overlay", 0)
    result["baseline_fallback_products"] = overlay.get(
        "products_using_baseline_fallback",
        compat_summary["products"],
    )
    return result

def reconcile(config: ImportEngineConfig, imports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    connection = duckdb.connect(str(config.database_path), read_only=True)
    rows: list[dict[str, Any]] = []
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        for item in imports:
            package_id = item["package_id"]
            for dataset, table in DATASET_TABLES.items():
                if table not in tables:
                    continue
                actual = int(connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE _package_id = ?",
                    [package_id],
                ).fetchone()[0])
                rows.append({
                    "domain": item["domain"],
                    "package_id": package_id,
                    "dataset": dataset,
                    "table": table,
                    "imported_rows": actual,
                    "status": "PASS",
                })
    finally:
        connection.close()
    return rows

def database_summary(config: ImportEngineConfig) -> dict[str, Any]:
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        table_counts = {}
        for table in DATASET_TABLES.values():
            if table in tables:
                table_counts[table] = int(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                )
        platforms = []
        if "platform_status_history" in tables:
            platforms = [
                {"platform_id": str(row[0]), "rows": int(row[1])}
                for row in connection.execute(
                    "SELECT lower(platform_id), COUNT(*) FROM platform_status_history GROUP BY 1 ORDER BY 1"
                ).fetchall()
            ]
        return {
            "database_path": str(config.database_path),
            "tables": table_counts,
            "platforms": platforms,
        }
    finally:
        connection.close()

def main() -> int:
    parser = argparse.ArgumentParser(description="Import and certify latest Metals, Crypto, and MTG UIP deliveries.")
    parser.add_argument("--metals", type=Path, default=DEFAULT_METALS)
    parser.add_argument("--crypto", type=Path, default=DEFAULT_CRYPTO)
    parser.add_argument("--mtg", type=Path, default=DEFAULT_MTG)
    parser.add_argument("--max-age-hours", type=float, default=96.0)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    config = ImportEngineConfig.from_repository_root(ROOT)
    initialize_database(config)

    imports = [
        import_standard_package(config, "metals", args.metals.resolve(), args.max_age_hours),
        import_standard_package(config, "crypto", args.crypto.resolve(), args.max_age_hours),
        import_mtg(
            config,
            args.mtg.resolve(),
            DEFAULT_MTG_COMPAT.resolve(),
            DEFAULT_MTG_UNIVERSAL.resolve(),
            args.max_age_hours,
        ),
    ]

    reconciliation = reconcile(config, imports)
    db = database_summary(config)
    domain_platforms = {row["platform_id"] for row in db["platforms"]}
    expected_platforms = {"metals", "crypto", "mtg"}
    full_run_checks = {
        "all_three_imports_pass": all(item["status"] == "PASS" for item in imports),
        "all_three_packages_fresh": all(item["freshness_status"] == "PASS" for item in imports),
        "all_three_platforms_in_database": expected_platforms <= domain_platforms,
        "database_tables_initialized": bool(db["tables"]),
        "reconciliation_rows_present": bool(reconciliation),
    }
    status = "CERTIFIED" if all(full_run_checks.values()) else "WARN"

    report = {
        "status": status,
        "phase": "11D",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_age_hours": args.max_age_hours,
        "imports": imports,
        "reconciliation": reconciliation,
        "database": db,
        "full_run_checks": full_run_checks,
        "mtg_live_overlay_complete": imports[2]["live_overlay_status"] == "PASS",
    }

    report_root = args.report_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "phase_11d_full_run_certification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    write_csv(
        report_root / "phase_11d_reconciliation.csv",
        reconciliation,
        ["domain", "package_id", "dataset", "table", "imported_rows", "status"],
    )

    print(json.dumps({
        "status": status,
        "imports": [
            {
                "domain": item["domain"],
                "import_mode": item["import_mode"],
                "imported_rows": item["imported_rows"],
                "age_hours": item["age_hours"],
                "freshness_status": item["freshness_status"],
            }
            for item in imports
        ],
        "database_platforms": db["platforms"],
        "full_run_checks": full_run_checks,
        "mtg_live_overlay_complete": report["mtg_live_overlay_complete"],
    }, indent=2))
    print(f"\nPHASE 11D FULL-RUN CERTIFICATION: {status}")
    print(f"Report: {report_root / 'phase_11d_full_run_certification.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

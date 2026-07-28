"""Governed manual MTG production cycle owned by UIP.

The sequence is intentionally fail-closed:
1. invoke the MTG production command;
2. validate the MTG handoff and source package;
3. adapt it to the universal contract;
4. validate and transactionally import it;
5. publish UIP-controlled intelligence and dashboard datasets.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

import duckdb

from foundation.import_engine.audit import apply_audit_registry_migration, synchronize_successful_import
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package

HANDOFF_CONTRACT = "mtg-to-uip-manual-production-v1"
HANDOFF_VERSION = "1.0"
INTERFACE_NAME = "mtg-governed-terminal-delivery"
INTERFACE_VERSION = "1.0"
ADAPTER_VERSION = "mtg-uip-handoff-adapter-1.0.0"
PLATFORM_ID = "MTG"
REQUIRED_ARTIFACTS = (
    "universal_mtg_consumption_interface.csv",
    "dashboard.csv",
    "forecasts.csv",
    "recommendations.csv",
    "rankings.csv",
    "exclusions.csv",
    "market_provenance.csv",
    "consumption_summary.json",
    "valuation_summary.json",
)


@dataclass(frozen=True)
class MTGProductionResult:
    status: str
    source_package_id: str
    universal_package_id: str
    import_id: str
    imported_rows: int
    dashboard_rows: int
    intelligence_rows: int
    source_command_ran: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _number(value: object) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _truth(value: object) -> bool:
    return str(value or "").strip().upper() in {"TRUE", "YES", "1", "Y"}


def _confidence(value: object) -> float | None:
    text = str(value or "").strip().upper()
    named = {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.5}
    if text in named:
        return named[text]
    number = _number(value)
    if number is None:
        return None
    if number > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def validate_handoff(mtg_root: Path, handoff_path: Path) -> tuple[dict[str, Any], Path]:
    root = mtg_root.resolve()
    handoff = _read_json(handoff_path.resolve())
    checks = {
        "status": handoff.get("status") == "READY_FOR_UIP_IMPORT",
        "contract": handoff.get("handoff_contract") == HANDOFF_CONTRACT,
        "version": handoff.get("handoff_version") == HANDOFF_VERSION,
        "platform": str(handoff.get("source_platform", "")).lower() == "mtg",
        "interface": handoff.get("interface_name") == INTERFACE_NAME,
        "interface_version": handoff.get("interface_version") == INTERFACE_VERSION,
        "product_count": int(handoff.get("governed_product_count", 0)) == 1141,
        "asking_not_history": handoff.get("current_asking_is_sold_history") is False,
        "asking_not_model": handoff.get("current_asking_model_eligible") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"MTG handoff contract failed: {failed}")

    package_root = (root / str(handoff["package_relative_path"])).resolve()
    try:
        package_root.relative_to(root)
    except ValueError as exc:
        raise ValueError("MTG handoff package escapes repository root") from exc
    if not package_root.is_dir():
        raise FileNotFoundError(str(package_root))

    artifacts = {row.get("filename"): row for row in handoff.get("artifacts", [])}
    for name in REQUIRED_ARTIFACTS:
        path = package_root / name
        metadata = artifacts.get(name)
        if not path.is_file() or not metadata:
            raise FileNotFoundError(f"Missing certified MTG artifact: {name}")
        if _sha256(path) != metadata.get("sha256"):
            raise ValueError(f"MTG artifact checksum mismatch: {name}")
    return handoff, package_root


def _asset_rows(source: list[dict[str, str]], run_id: str, generated: str) -> list[dict[str, Any]]:
    return [{
        "run_id": run_id,
        "universal_asset_id": row["canonical_product_id"],
        "platform_asset_id": row["canonical_product_id"],
        "platform_id": PLATFORM_ID,
        "asset_name": row.get("canonical_product_name", ""),
        "asset_symbol": "",
        "asset_class": "COLLECTIBLE",
        "asset_subclass": row.get("product_class", "MTG"),
        "currency": row.get("currency") or "USD",
        "investable": row.get("valuation_state") != "VALUATION_UNAVAILABLE",
        "active": True,
        "source_system": "mtg-investment-terminal",
        "source_record_id": row["canonical_product_id"],
        "first_observed_date": "",
        "last_observed_date": row.get("selected_reference_date", ""),
        "last_updated_at_utc": generated,
        "notes": row.get("valuation_state", ""),
        "metadata_json": json.dumps({
            "selected_reference_price": row.get("selected_reference_price", ""),
            "selected_source_type": row.get("selected_source_type", ""),
            "freshness_state": row.get("freshness_state", ""),
            "dashboard_eligible": _truth(row.get("dashboard_eligible")),
            "model_eligible": _truth(row.get("model_eligible")),
        }, sort_keys=True),
    } for row in source]


def _forecast_rows(source: list[dict[str, str]], run_id: str, generated: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source:
        current = _number(row.get("selected_reference_price"))
        confidence = _confidence(row.get("confidence"))
        for prefix, months in (("one_year", 12), ("three_year", 36), ("five_year", 60)):
            point = _number(row.get(f"{prefix}_base_usd"))
            if point is None:
                continue
            rows.append({
                "run_id": run_id,
                "universal_asset_id": row["canonical_product_id"],
                "platform_id": PLATFORM_ID,
                "forecast_origin_date": generated[:10],
                "forecast_horizon_months": months,
                "forecast_method": row.get("forecast_method", ""),
                "point_forecast": point,
                "lower_bound": _number(row.get(f"{prefix}_downside_usd")) or "",
                "upper_bound": _number(row.get(f"{prefix}_upside_usd")) or "",
                "expected_return": "" if not current else point / current - 1,
                "probability_positive": "",
                "confidence_score": confidence if confidence is not None else "",
                "scenario": prefix.upper(),
                "source_system": "mtg-investment-terminal",
                "model_version": ADAPTER_VERSION,
                "generated_at_utc": generated,
                "notes": row.get("forecast_consumption_state", ""),
                "metadata_json": json.dumps({
                    "governed_forecast_eligible": _truth(row.get("governed_forecast_eligible")),
                    "valuation_state": row.get("valuation_state", ""),
                }, sort_keys=True),
            })
    return rows


def _recommendation_rows(source: list[dict[str, str]], run_id: str, generated: str) -> list[dict[str, Any]]:
    rows = []
    for row in source:
        score = _number(row.get("guarded_rank_score"))
        rows.append({
            "run_id": run_id,
            "universal_asset_id": row["canonical_product_id"],
            "platform_id": PLATFORM_ID,
            "recommendation": row.get("legacy_recommendation_action", ""),
            "normalized_score": "" if score is None else max(0.0, min(1.0, (score + 100) / 200)),
            "confidence_score": _confidence(row.get("confidence")) or "",
            "target_weight": "",
            "minimum_weight": "",
            "maximum_weight": "",
            "rationale": row.get("recommendation_consumption_state", ""),
            "risk_summary": row.get("suppression_reason", ""),
            "time_horizon_months": 36,
            "source_system": "mtg-investment-terminal",
            "model_version": ADAPTER_VERSION,
            "generated_at_utc": generated,
            "metadata_json": json.dumps({
                "guarded_rank": row.get("guarded_rank", ""),
                "guarded_rank_score": row.get("guarded_rank_score", ""),
                "governed_recommendation_eligible": _truth(row.get("governed_recommendation_eligible")),
            }, sort_keys=True),
        })
    return rows


def build_universal_package(package_root: Path, handoff: dict[str, Any], destination: Path) -> Path:
    generated = _utc_now()
    run_id = str(handoff["package_id"])
    package_id = f"{run_id}-uip-handoff-v1"
    interface = _read_csv(package_root / "universal_mtg_consumption_interface.csv")
    forecasts = _read_csv(package_root / "forecasts.csv")
    recommendations = _read_csv(package_root / "recommendations.csv")
    datasets: dict[str, list[dict[str, Any]]] = {
        "asset_master": _asset_rows(interface, run_id, generated),
        "forecasts": _forecast_rows(forecasts, run_id, generated),
        "recommendations": _recommendation_rows(recommendations, run_id, generated),
        "platform_status": [{
            "run_id": run_id,
            "platform_id": PLATFORM_ID,
            "platform_name": "MTG Investment Terminal",
            "platform_version": INTERFACE_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "contract_version": "v1",
            "run_status": "PASS",
            "run_started_at_utc": generated,
            "run_completed_at_utc": generated,
            "data_as_of_date": generated[:10],
            "records_published": len(interface),
            "warning_count": 0,
            "error_count": 0,
            "status_message": "Validated Phase 11E.17 governed handoff",
            "generated_at_utc": generated,
            "package_id": package_id,
        }],
    }

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mtg-uip-", dir=destination.parent) as temp:
        stage = Path(temp) / "latest"
        stage.mkdir()
        manifest = []
        for name, rows in datasets.items():
            path = stage / f"{name}.csv"
            _write_csv(path, list(rows[0]), rows)
            manifest.append({"dataset_name": name, "filename": path.name, "row_count": len(rows), "sha256": _sha256(path), "required": True, "validation_status": "PASS"})
        _write_csv(stage / "export_manifest.csv", ["dataset_name", "filename", "row_count", "sha256", "required", "validation_status"], manifest)
        (stage / "package_summary.json").write_text(json.dumps({
            "status": "PASS", "package_id": package_id, "platform_id": PLATFORM_ID,
            "run_id": run_id, "adapter_version": ADAPTER_VERSION, "contract_version": "v1",
            "generated_at_utc": generated, "source_handoff_contract": HANDOFF_CONTRACT,
            "source_package_id": handoff["package_id"],
            "dataset_counts": {name: len(rows) for name, rows in datasets.items()},
        }, indent=2) + "\n", encoding="utf-8")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(stage), str(destination))
    return destination


def publish_uip_datasets(config: ImportEngineConfig, package_id: str, output_root: Path) -> tuple[int, int]:
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        intelligence = connection.execute("""
            SELECT a.universal_asset_id, a.asset_name, a.asset_subclass,
                   f.forecast_horizon_months, f.point_forecast, f.lower_bound,
                   f.upper_bound, f.expected_return, f.confidence_score,
                   r.recommendation, r.normalized_score, r.rationale, r.risk_summary
            FROM asset_master_history a
            LEFT JOIN forecasts_history f USING (_package_id, universal_asset_id)
            LEFT JOIN recommendations_history r USING (_package_id, universal_asset_id)
            WHERE a._package_id = ?
            ORDER BY a.universal_asset_id, f.forecast_horizon_months
        """, [package_id]).fetchdf()
        dashboard = connection.execute("""
            SELECT a.universal_asset_id, a.asset_name, a.asset_subclass, a.currency,
                   a.investable, a.last_observed_date, a.notes AS valuation_state,
                   MAX(CASE WHEN f.forecast_horizon_months=12 THEN f.point_forecast END) AS one_year_base,
                   MAX(CASE WHEN f.forecast_horizon_months=36 THEN f.point_forecast END) AS three_year_base,
                   MAX(CASE WHEN f.forecast_horizon_months=60 THEN f.point_forecast END) AS five_year_base,
                   MAX(r.recommendation) AS recommendation,
                   MAX(r.normalized_score) AS normalized_score
            FROM asset_master_history a
            LEFT JOIN forecasts_history f USING (_package_id, universal_asset_id)
            LEFT JOIN recommendations_history r USING (_package_id, universal_asset_id)
            WHERE a._package_id = ?
            GROUP BY ALL
            ORDER BY a.universal_asset_id
        """, [package_id]).fetchdf()
    finally:
        connection.close()

    output_root.mkdir(parents=True, exist_ok=True)
    intelligence.to_csv(output_root / "mtg_intelligence.csv", index=False)
    dashboard.to_csv(output_root / "mtg_dashboard.csv", index=False)
    (output_root / "publication_status.json").write_text(json.dumps({
        "status": "PASS", "package_id": package_id, "published_at_utc": _utc_now(),
        "intelligence_rows": len(intelligence), "dashboard_rows": len(dashboard),
        "source": "UIP universal database after successful import",
    }, indent=2) + "\n", encoding="utf-8")
    return len(dashboard), len(intelligence)


def run_mtg_manual_production_cycle(repository_root: Path, mtg_root: Path, *, skip_source_run: bool = False) -> MTGProductionResult:
    repository_root = repository_root.resolve()
    mtg_root = mtg_root.resolve()
    command = [sys.executable, "scripts/run_phase_11e_17_manual_uip_handoff.py"]
    if not skip_source_run:
        completed = subprocess.run(command, cwd=mtg_root)
        if completed.returncode:
            raise RuntimeError(f"MTG production command failed: {completed.returncode}")

    handoff_path = mtg_root / "data/operations/mtg_uip_handoff/latest_mtg_uip_handoff.json"
    handoff, source_package = validate_handoff(mtg_root, handoff_path)
    universal_package = build_universal_package(
        source_package, handoff, repository_root / "data/integration/mtg/latest"
    )

    config = ImportEngineConfig.from_repository_root(repository_root)
    initialize_database(config)
    apply_audit_registry_migration(config)
    package = discover_package(universal_package)
    validation = validate_package_integrity(package)
    if not validation.passed:
        raise RuntimeError(f"UIP MTG package validation failed with {validation.error_count} errors")

    try:
        imported = import_package(config, universal_package)
        synchronize_successful_import(config, import_id=imported.import_id)
        import_id = imported.import_id
        imported_rows = imported.imported_row_count
    except DuplicatePackageError:
        connection = duckdb.connect(str(config.database_path), read_only=True)
        try:
            row = connection.execute("""
                SELECT successful_import_id FROM universal_packages WHERE package_id = ?
            """, [package.identity.package_id]).fetchone()
        finally:
            connection.close()
        if not row or not row[0]:
            raise
        import_id = str(row[0])
        imported_rows = 0

    dashboard_rows, intelligence_rows = publish_uip_datasets(
        config, package.identity.package_id,
        repository_root / "data/operations/uip_mtg/latest",
    )
    result = MTGProductionResult(
        "PASS", str(handoff["package_id"]), package.identity.package_id,
        import_id, imported_rows, dashboard_rows, intelligence_rows,
        not skip_source_run,
    )
    state = repository_root / "data/operations/uip_mtg/last_successful_cycle.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return result

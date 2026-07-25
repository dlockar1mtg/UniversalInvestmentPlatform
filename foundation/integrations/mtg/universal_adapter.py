"""Adapt the certified MTG Phase 10.10 export into a Universal package."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import shutil

MISSING = ""
EXPECTED_PRODUCTS = 1141
EXPECTED_FORECAST_ELIGIBLE = 1103
EXPECTED_RECOMMENDATION_ELIGIBLE = 694
ADAPTER_VERSION = "mtg-import-adapter-1.0.0"
CONTRACT_VERSION = "v1"
PLATFORM_ID = "MTG"

SOURCE_FILES = (
    "asset_master.csv",
    "forecasts.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "portfolio_summary.csv",
    "platform_status.csv",
    "diagnostics.csv",
    "export_manifest.json",
    "package_summary.json",
)


@dataclass(frozen=True)
class MTGAdapterResult:
    package_path: Path
    package_id: str
    run_id: str
    dataset_rows: dict[str, int]
    source_products: int
    source_forecast_eligible: int
    source_recommendation_eligible: int
    source_package_id: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean(value: object) -> str:
    return str(value or "").strip()


def _number(value: object) -> float | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _bool(value: object) -> bool:
    return _clean(value).upper() in {"YES", "TRUE", "1", "Y"}


def _confidence(value: object) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if number > 1 and number <= 100:
        number /= 100
    return max(0.0, min(1.0, number))


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _validate_source(source: Path) -> dict[str, Any]:
    missing = [name for name in SOURCE_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing MTG export files: " + ", ".join(missing))
    summary = json.loads((source / "package_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((source / "export_manifest.json").read_text(encoding="utf-8"))
    if summary.get("status") != "PASS":
        raise ValueError("MTG source package status is not PASS")
    if summary.get("source_closeout_status") != "PRODUCTION_CLOSED":
        raise ValueError("MTG Phase 10.9 source is not PRODUCTION_CLOSED")
    if int(summary.get("products", 0)) != EXPECTED_PRODUCTS:
        raise ValueError("MTG source product count does not equal 1,141")
    if int(summary.get("diagnostics", -1)) != 0:
        raise ValueError("MTG source package contains diagnostics")
    if summary.get("privacy_boundary", {}).get("position_level_holdings_exported") is not False:
        raise ValueError("MTG source package violates the privacy boundary")
    for filename, metadata in manifest.get("files", {}).items():
        path = source / filename
        if not path.is_file() or _sha256(path) != metadata.get("sha256"):
            raise ValueError(f"MTG source hash mismatch: {filename}")
    return summary


def _forecast_rows(source_rows: list[dict[str, str]], run_id: str, generated: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        asset_id = _clean(source.get("asset_id"))
        current = _number(source.get("current_market_value_usd"))
        method = _clean(source.get("forecast_method"))
        confidence = _confidence(source.get("confidence"))
        common = {
            "run_id": run_id,
            "universal_asset_id": asset_id,
            "platform_id": PLATFORM_ID,
            "forecast_origin_date": generated[:10],
            "forecast_method": method,
            "probability_positive": MISSING,
            "confidence_score": confidence if confidence is not None else MISSING,
            "source_system": "mtg-investment-terminal",
            "model_version": ADAPTER_VERSION,
            "generated_at_utc": generated,
        }

        scenarios: list[tuple[str, str, str, str, int | None]] = []
        if _number(source.get("native_forecast_base_usd")) is not None:
            scenarios.append((
                "native_forecast_low_usd",
                "native_forecast_base_usd",
                "native_forecast_high_usd",
                "NATIVE",
                None,
            ))
        for prefix, months in (("one_year", 12), ("three_year", 36), ("five_year", 60)):
            base_field = f"{prefix}_base_usd"
            if _number(source.get(base_field)) is not None:
                scenarios.append((
                    f"{prefix}_downside_usd",
                    base_field,
                    f"{prefix}_upside_usd",
                    prefix.upper(),
                    months,
                ))

        for low_field, base_field, high_field, scenario, months in scenarios:
            point = _number(source.get(base_field))
            expected_return = None
            if current not in (None, 0) and point is not None:
                expected_return = point / current - 1
            rows.append({
                **common,
                "forecast_horizon_months": months if months is not None else MISSING,
                "point_forecast": point if point is not None else MISSING,
                "lower_bound": _number(source.get(low_field)) or MISSING,
                "upper_bound": _number(source.get(high_field)) or MISSING,
                "expected_return": expected_return if expected_return is not None else MISSING,
                "scenario": scenario,
                "notes": _clean(source.get("forecast_status")),
                "metadata_json": _json({
                    "forecast_eligible": _bool(source.get("forecast_eligible")),
                    "source_confidence": _clean(source.get("confidence")),
                    "currency": _clean(source.get("currency")) or "USD",
                }),
            })
    return rows


def build_universal_mtg_package(source_package: Path, output_package: Path) -> MTGAdapterResult:
    source = source_package.resolve()
    summary = _validate_source(source)
    assets = _read_csv(source / "asset_master.csv")
    forecasts = _read_csv(source / "forecasts.csv")
    recommendations = _read_csv(source / "recommendations.csv")
    risks = _read_csv(source / "risk_metrics.csv")
    source_status = _read_csv(source / "platform_status.csv")[0]

    generated = datetime.now(timezone.utc).isoformat()
    source_package_id = _clean(summary.get("package_id"))
    run_id = source_package_id
    package_id = f"{source_package_id}-uip-v1"
    output = output_package.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    asset_rows = [{
        "run_id": run_id,
        "universal_asset_id": row["asset_id"],
        "platform_asset_id": row["source_product_id"],
        "platform_id": PLATFORM_ID,
        "asset_name": row["asset_name"],
        "asset_symbol": MISSING,
        "asset_class": row.get("asset_class", "MTG"),
        "asset_subclass": row.get("asset_subclass", MISSING),
        "currency": row.get("currency", "USD"),
        "investable": True,
        "active": True,
        "source_system": "mtg-investment-terminal",
        "source_record_id": row["source_product_id"],
        "first_observed_date": row.get("release_date", MISSING),
        "last_observed_date": generated[:10],
        "last_updated_at_utc": generated,
        "notes": MISSING,
        "metadata_json": _json({
            "product_class": row.get("product_class", MISSING),
            "canonical_set_name": row.get("canonical_set_name", MISSING),
            "registry_status": row.get("registry_status", MISSING),
        }),
    } for row in assets]

    forecast_rows = _forecast_rows(forecasts, run_id, generated)

    recommendation_rows = [{
        "run_id": run_id,
        "universal_asset_id": row["asset_id"],
        "platform_id": PLATFORM_ID,
        "recommendation": row.get("recommendation_action", MISSING),
        "normalized_score": MISSING,
        "confidence_score": _confidence(row.get("confidence")) or MISSING,
        "target_weight": MISSING,
        "minimum_weight": MISSING,
        "maximum_weight": MISSING,
        "rationale": row.get("recommendation_rationale", MISSING),
        "risk_summary": row.get("suppression_reason", MISSING),
        "time_horizon_months": MISSING,
        "source_system": "mtg-investment-terminal",
        "model_version": ADAPTER_VERSION,
        "generated_at_utc": generated,
        "metadata_json": _json({
            "recommendation_eligible": _bool(row.get("recommendation_eligible")),
            "recommendation_status": row.get("recommendation_status", MISSING),
            "currency": row.get("currency", "USD"),
        }),
    } for row in recommendations]

    risk_rows = [{
        "run_id": run_id,
        "universal_asset_id": row["asset_id"],
        "platform_id": PLATFORM_ID,
        "risk_score": MISSING,
        "risk_level": row.get("quality_disposition", MISSING),
        "volatility": MISSING,
        "downside_volatility": MISSING,
        "maximum_drawdown": MISSING,
        "value_at_risk": MISSING,
        "expected_shortfall": MISSING,
        "beta": MISSING,
        "liquidity_score": MISSING,
        "concentration_score": MISSING,
        "source_system": "mtg-investment-terminal",
        "model_version": ADAPTER_VERSION,
        "generated_at_utc": generated,
        "notes": row.get("suppression_reason", MISSING),
        "metadata_json": _json({
            "admission_tier": row.get("admission_tier", MISSING),
            "forecast_eligible": _bool(row.get("forecast_eligible")),
            "recommendation_eligible": _bool(row.get("recommendation_eligible")),
            "source_confidence": row.get("confidence", MISSING),
        }),
    } for row in risks]

    status_rows = [{
        "run_id": run_id,
        "platform_id": PLATFORM_ID,
        "platform_name": "MTG Investment Terminal",
        "platform_version": source_status.get("interface_name", "mtg-universal-export-v1"),
        "adapter_version": ADAPTER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "run_status": "PASS",
        "run_started_at_utc": generated,
        "run_completed_at_utc": generated,
        "data_as_of_date": generated[:10],
        "records_published": len(asset_rows) + len(forecast_rows) + len(recommendation_rows) + len(risk_rows),
        "warning_count": 0,
        "error_count": 0,
        "status_message": "Phase 10.11 MTG canonical package ready for import",
        "generated_at_utc": generated,
        "package_id": package_id,
    }]

    datasets = {
        "asset_master": asset_rows,
        "forecasts": forecast_rows,
        "recommendations": recommendation_rows,
        "risk_metrics": risk_rows,
        "platform_status": status_rows,
    }
    for name, rows in datasets.items():
        _write_csv(output / f"{name}.csv", list(rows[0]), rows)

    manifest_rows = [{
        "dataset_name": name,
        "filename": f"{name}.csv",
        "row_count": len(rows),
        "sha256": _sha256(output / f"{name}.csv"),
        "required": True,
        "validation_status": "PASS",
    } for name, rows in datasets.items()]
    _write_csv(
        output / "export_manifest.csv",
        ["dataset_name", "filename", "row_count", "sha256", "required", "validation_status"],
        manifest_rows,
    )

    package_summary = {
        "status": "PASS",
        "package_id": package_id,
        "source_package_id": source_package_id,
        "platform_id": PLATFORM_ID,
        "run_id": run_id,
        "adapter_version": ADAPTER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": generated,
        "source_products": int(summary["products"]),
        "source_forecast_eligible": int(summary["forecast_eligible"]),
        "source_recommendation_eligible": int(summary["recommendation_eligible"]),
        "source_portfolio_summary_rows": int(summary["portfolio_summary_rows"]),
        "position_level_holdings_imported": False,
        "dataset_rows": {name: len(rows) for name, rows in datasets.items()},
        "source_package_sha256": _sha256(source / "package_summary.json"),
        "quota_calls": 0,
    }
    (output / "package_summary.json").write_text(
        json.dumps(package_summary, indent=2), encoding="utf-8"
    )

    if len(asset_rows) != EXPECTED_PRODUCTS:
        raise ValueError("Adapted asset count does not equal 1,141")
    if len(recommendation_rows) != EXPECTED_PRODUCTS or len(risk_rows) != EXPECTED_PRODUCTS:
        raise ValueError("Adapted recommendation or risk count does not reconcile")
    return MTGAdapterResult(
        package_path=output,
        package_id=package_id,
        run_id=run_id,
        dataset_rows={name: len(rows) for name, rows in datasets.items()},
        source_products=int(summary["products"]),
        source_forecast_eligible=int(summary["forecast_eligible"]),
        source_recommendation_eligible=int(summary["recommendation_eligible"]),
        source_package_id=source_package_id,
    )

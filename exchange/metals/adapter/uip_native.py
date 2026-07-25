"""Publish a Universal Metals package without an external Metals root."""
from __future__ import annotations

import csv
import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "1.0.0"
ADAPTER_VERSION = "uip-native-metals-1.0.0"
PLATFORM_ID = "metals"


@dataclass(frozen=True)
class NativePackageResult:
    package_id: str
    run_id: str
    package_root: str
    dataset_count: int
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _add_months(value: str, months: int) -> str:
    start = date.fromisoformat(value)
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, 28)
    return date(year, month, day).isoformat()


def publish_uip_native_metals_package(
    native_cycle_path: Path,
    output_root: Path,
    *,
    run_id: str | None = None,
    generated_at_utc: str | None = None,
) -> NativePackageResult:
    document = json.loads(native_cycle_path.read_text(encoding="utf-8-sig"))
    forecasts = document.get("forecasts", [])
    if document.get("status") != "PASS" or not forecasts:
        raise ValueError("A passing UIP-native forecast cycle is required.")

    generated = generated_at_utc or datetime.now(timezone.utc).isoformat()
    run = run_id or str(uuid.uuid4())
    package_id = f"metals-native-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    package_root = output_root / package_id
    package_root.mkdir(parents=True, exist_ok=False)

    assets: dict[str, dict[str, object]] = {}
    forecast_rows: list[dict[str, object]] = []
    recommendation_rows: list[dict[str, object]] = []
    for row in forecasts:
        asset_id = str(row["asset_id"])
        universal_id = f"metals:{asset_id.lower()}"
        assets[asset_id] = {
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "universal_asset_id": universal_id,
            "platform_asset_id": asset_id,
            "asset_name": asset_id.title(),
            "asset_symbol": asset_id,
            "asset_class": "metals",
            "asset_subclass": "commodity_benchmark",
            "currency": "USD",
            "market_or_region": "global",
            "is_active": True,
            "investable": True,
            "liquidity_tier": "high",
            "data_source": "UIP-native Metals store",
            "first_available_date": row["as_of_date"],
            "last_updated_at_utc": generated,
        }
        forecast_rows.append({
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "universal_asset_id": universal_id,
            "forecast_origin_date": row["as_of_date"],
            "forecast_horizon_months": row["horizon_months"],
            "forecast_date": _add_months(str(row["as_of_date"]), int(row["horizon_months"])),
            "current_value": row["current_value"],
            "forecast_value_base": row["projected_value"],
            "forecast_value_bear": "",
            "forecast_value_bull": "",
            "expected_total_return": row["expected_return"],
            "expected_cagr": row["annualized_return"],
            "probability_positive_return": "",
            "forecast_confidence": round(float(row["confidence"]) * 100, 2),
            "forecast_method": row["model_id"],
            "scenario_name": "base",
            "model_version": row["methodology_version"],
            "generated_at_utc": generated,
        })
        recommendation_rows.append({
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "universal_asset_id": universal_id,
            "recommendation_date": row["as_of_date"],
            "recommendation": row["recommendation"],
            "recommendation_score": round(float(row["expected_return"]) * 100, 6),
            "confidence": round(float(row["confidence"]) * 100, 2),
            "time_horizon_months": row["horizon_months"],
            "rationale": f"UIP-native {row['model_id']} forecast",
            "model_version": row["methodology_version"],
            "generated_at_utc": generated,
        })

    datasets = {
        "asset_master": (list(assets.values()), list(next(iter(assets.values())).keys())),
        "forecasts": (forecast_rows, list(forecast_rows[0].keys())),
        "recommendations": (recommendation_rows, list(recommendation_rows[0].keys())),
        "platform_status": ([{
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "status": "HEALTHY",
            "status_date": generated[:10],
            "data_as_of_date": max(str(row["as_of_date"]) for row in forecasts),
            "last_successful_run_at_utc": generated,
            "adapter_version": ADAPTER_VERSION,
            "message": "UIP-native Metals package generated without external runtime",
            "generated_at_utc": generated,
        }], ["contract_version", "platform_id", "run_id", "status", "status_date", "data_as_of_date", "last_successful_run_at_utc", "adapter_version", "message", "generated_at_utc"]),
    }

    manifest_rows: list[dict[str, object]] = []
    for dataset_name, (rows, columns) in datasets.items():
        path = package_root / f"{dataset_name}.csv"
        _write_csv(path, columns, rows)
        manifest_rows.append({
            "package_id": package_id,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "adapter_version": ADAPTER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "dataset_name": dataset_name,
            "filename": path.name,
            "row_count": len(rows),
            "file_size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "generated_at_utc": generated,
            "required": dataset_name == "platform_status",
            "validation_status": "PASS",
        })

    manifest_path = package_root / "export_manifest.csv"
    _write_csv(manifest_path, list(manifest_rows[0].keys()), manifest_rows)
    summary = {
        "package_id": package_id,
        "platform_id": PLATFORM_ID,
        "run_id": run,
        "adapter_version": ADAPTER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": generated,
        "data_as_of_date": max(str(row["as_of_date"]) for row in forecasts),
        "validation_status": "PASS",
        "dataset_count": len(datasets),
    }
    (package_root / "package_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "latest.json").write_text(json.dumps({**summary, "package_root": str(package_root)}, indent=2) + "\n", encoding="utf-8")
    return NativePackageResult(package_id, run, str(package_root), len(datasets), "PASS")

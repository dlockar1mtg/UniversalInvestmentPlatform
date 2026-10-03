"""Publish a Universal Metals package without an external Metals root."""
from __future__ import annotations

import csv
import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from foundation.production.metals_registry import load_metals_registry

CONTRACT_VERSION = "1.0.0"
ADAPTER_VERSION = "uip-native-metals-1.0.0"
PLATFORM_ID = "metals"
PLATFORM_NAME = "Metals Intelligence Platform"
PLATFORM_VERSION = "1.0.0"


@dataclass(frozen=True)
class NativePackageResult:
    package_id: str
    run_id: str
    package_root: str
    dataset_count: int
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _descriptive_columns(components: dict[str, object]) -> dict[str, object]:
    """Valuation, trend and the historical 12-month range as extra forecast columns.

    The importer keeps columns outside the forecast contract in metadata_json
    (unmapped_contract_fields), which is how they reach the dashboard without a
    contract change. Every row gets every key, blank when not available.
    """
    descriptive = components.get("descriptive") if isinstance(components, dict) else None
    descriptive = descriptive if isinstance(descriptive, dict) else {}
    valuation = descriptive.get("valuation") or {}
    trend = descriptive.get("trend") or {}
    band = descriptive.get("historical_12m_returns") or {}
    return {
        "valuation_gap_10y": valuation.get("gap", ""),
        "valuation_state": valuation.get("state", ""),
        "trend_gap_12m": trend.get("gap", ""),
        "trend_state": trend.get("state", ""),
        "historical_12m_return_p10": band.get("p10", ""),
        "historical_12m_return_p50": band.get("p50", ""),
        "historical_12m_return_p90": band.get("p90", ""),
        "historical_12m_return_samples": band.get("samples", ""),
    }

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


def _standard_recommendation(value: object) -> tuple[str, str]:
    native = str(value or "").strip().upper()
    mapping = {
        "STRONG_BUY": "strong_buy",
        "BUY": "buy",
        "HOLD": "hold",
        "REDUCE": "reduce",
        # AVOID is a bearish call, not a data-readiness state; map it the way
        # the Crypto domain does (normalization._RECOMMENDATION_MAP).
        "AVOID": "sell",
    }
    try:
        return mapping[native], native
    except KeyError as exc:
        raise ValueError(
            f"Unsupported native Metals recommendation: {native or '<blank>'}"
        ) from exc


def _normalized_recommendation_score(expected_return: object) -> float:
    raw = float(expected_return) * 100.0
    return round(min(100.0, max(0.0, raw)), 6)


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

    registry = load_metals_registry()
    assets_by_id = registry.assets_by_id
    assets_by_slug = registry.assets_by_slug

    assets: dict[str, dict[str, object]] = {}
    forecast_rows: list[dict[str, object]] = []
    recommendation_rows: list[dict[str, object]] = []
    risk_rows: dict[str, dict[str, object]] = {}
    for row in forecasts:
        asset_id = str(row["asset_id"]).strip()
        native_key = asset_id.lower()
        canonical_asset = assets_by_id.get(native_key)
        if canonical_asset is None:
            canonical_asset = assets_by_slug.get(native_key)
        if canonical_asset is None:
            raise ValueError(
                f"Native Metals asset is not present in the canonical registry: {asset_id}"
            )
        if canonical_asset.asset_class != "commodity":
            raise ValueError(
                f"Native Metals forecast asset is not a governed commodity: {asset_id}"
            )
        universal_id = canonical_asset.asset_id
        components = json.loads(str(row.get("component_json") or "{}"))
        risk = components.get("risk")
        if int(row["horizon_months"]) == 12 and isinstance(risk, dict) and universal_id not in risk_rows:
            # Risk of the benchmark itself, from its monthly history (one row per metal).
            risk_rows[universal_id] = {
                "contract_version": CONTRACT_VERSION,
                "platform_id": PLATFORM_ID,
                "run_id": run,
                "universal_asset_id": universal_id,
                "as_of_date": row["as_of_date"],
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "annualized_volatility": risk["annualized_volatility"],
                "maximum_drawdown": risk["maximum_drawdown"],
                "downside_deviation": risk["downside_deviation"],
                "value_at_risk_95": risk["value_at_risk_95"],
                "risk_notes": (
                    f"Monthly benchmark history: {risk['return_observations']} monthly returns "
                    f"over {risk['lookback_months']} months; VaR is monthly."
                ),
                "lookback_days": int(round(int(risk["lookback_months"]) * 30.4375)),
                "generated_at_utc": generated,
            }
        assets[asset_id] = {
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "universal_asset_id": universal_id,
            "platform_asset_id": asset_id,
            "asset_name": canonical_asset.name,
            "asset_symbol": canonical_asset.symbol,
            "asset_class": "metals",
            "asset_subclass": "commodity_benchmark",
            "currency": "USD",
            "market_or_region": "",
            "is_active": True,
            "investable": False,
            "liquidity_tier": "",
            "data_source": "UIP-native Metals store",
            "first_available_date": "",
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
            **_descriptive_columns(components),
            "forecast_value_base": row["projected_value"],
            "forecast_value_bear": "" if components.get("bear_value") is None else components["bear_value"],
            "forecast_value_bull": "" if components.get("bull_value") is None else components["bull_value"],
            "expected_total_return": row["expected_return"],
            "expected_cagr": row["annualized_return"],
            "probability_positive_return": (
                "" if components.get("probability_positive_return") is None
                else components["probability_positive_return"]
            ),
            "forecast_confidence": round(float(row["confidence"]) * 100, 2),
            "forecast_method": row["model_id"],
            "scenario_name": "base",
            "model_version": row["methodology_version"],
            "generated_at_utc": generated,
        })
        universal_recommendation, native_recommendation = (
            _standard_recommendation(row["recommendation"])
        )
        recommendation_rows.append({
            "contract_version": CONTRACT_VERSION,
            "platform_id": PLATFORM_ID,
            "run_id": run,
            "universal_asset_id": universal_id,
            "as_of_date": row["as_of_date"],
            "recommendation": universal_recommendation,
            "normalized_score": _normalized_recommendation_score(
                row["expected_return"]
            ),
            "confidence_score": round(float(row["confidence"]) * 100, 2),
            "platform_native_score": "",
            "platform_native_label": native_recommendation,
            "time_horizon": f"{int(row['horizon_months'])}_month",
            "target_weight": "",
            "minimum_weight": "",
            "maximum_weight": "",
            "rationale_summary": f"UIP-native {row['model_id']} forecast",
            "primary_risk": "",
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
            "platform_name": PLATFORM_NAME,
            "platform_version": PLATFORM_VERSION,
            "run_id": run,
            "run_started_at_utc": generated,
            "run_completed_at_utc": generated,
            "run_status": "success",
            "data_as_of_date": max(str(row["as_of_date"]) for row in forecasts),
            "records_published": len(forecast_rows),
            "warning_count": 0,
            "error_count": 0,
            "source_machine": "",
            "message": "UIP-native Metals package generated without external runtime",
        }], [
            "contract_version",
            "platform_id",
            "platform_name",
            "platform_version",
            "run_id",
            "run_started_at_utc",
            "run_completed_at_utc",
            "run_status",
            "data_as_of_date",
            "records_published",
            "warning_count",
            "error_count",
            "source_machine",
            "message",
        ]),
    }

    if risk_rows:
        datasets["risk_metrics"] = (list(risk_rows.values()), list(next(iter(risk_rows.values())).keys()))

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

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from foundation.intelligence.cross_domain.contracts import DOMAIN_SCHEMA_VERSION

DEPLOYABLE_SIGNALS = {"STRONG_BUY", "BUY", "ACCUMULATE"}
REQUIRED_FILES = (
    "asset_master.csv",
    "forecasts.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "portfolio_positions.csv",
    "platform_status.csv",
)
DEFAULT_FORECAST_HORIZON_MONTHS = 12
VEHICLE_TO_COMMODITY = {
    "GLD": "metals:commodity:gold",
    "IAU": "metals:commodity:gold",
    "SGOL": "metals:commodity:gold",
    "SLV": "metals:commodity:silver",
    "SIVR": "metals:commodity:silver",
    "PPLT": "metals:commodity:platinum",
    "CPER": "metals:commodity:copper",
    "COPX": "metals:commodity:copper",
    "URA": "metals:commodity:uranium",
}


def _number(value: object, default: float = 0.0) -> float:
    try:
        text = str(value or "").replace("$", "").replace(",", "").strip()
        return float(text) if text else default
    except ValueError:
        return default


def _optional_number(value: object) -> float | None:
    text = str(value or "").replace("$", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _first(row: dict[str, Any], *fields: str, default: object = "") -> object:
    for field in fields:
        value = row.get(field)
        if value is not None and str(value).strip() != "":
            return value
    return default


def _ticker_from_asset_id(asset_id: str) -> str:
    if ":vehicle:" not in asset_id:
        return ""
    return asset_id.rsplit(":", 1)[-1].upper()


def _forecast_asset_id(asset_id: str) -> str:
    ticker = _ticker_from_asset_id(asset_id)
    return VEHICLE_TO_COMMODITY.get(ticker, asset_id)


def _normalized_signal(action: object, score: float, expected_return: float | None) -> str:
    raw = str(action or "").strip().upper().replace(" ", "_")
    aliases = {
        "STRONG_BUY": "STRONG_BUY",
        "BUY": "BUY",
        "ACCUMULATE": "ACCUMULATE",
        "HOLD": "HOLD",
        "WAIT": "WATCH",
        "WATCH": "WATCH",
        "RESERVE_BUY": "WATCH",
        "AVOID": "AVOID",
        "SELL": "AVOID",
        "REDUCE": "AVOID",
    }
    if raw in {"STRONG_BUY", "BUY", "ACCUMULATE"}:
        return aliases[raw] if expected_return is not None and expected_return > 0 else "WATCH"
    if raw in aliases:
        return aliases[raw]
    if expected_return is None:
        return "WATCH" if score >= 50 else "HOLD"
    if score >= 75 and expected_return > 0:
        return "STRONG_BUY"
    if score >= 60 and expected_return > 0:
        return "BUY"
    if score >= 50:
        return "WATCH"
    return "HOLD"


def _platform_ready(rows: list[dict[str, str]]) -> tuple[bool, list[str]]:
    if not rows:
        return False, ["METALS_PLATFORM_STATUS_MISSING"]
    reasons: list[str] = []
    ready = True
    for row in rows:
        status = str(row.get("status") or "").strip().upper()
        run_status = str(row.get("run_status") or "").strip().upper()
        warnings = int(_number(row.get("warning_count"), 0))
        errors = int(_number(row.get("error_count"), 0))
        explicit_ready = status in {"READY", "PASS", "SUCCESS"}
        legacy_success = not status and run_status == "SUCCESS" and warnings == 0 and errors == 0
        if not (explicit_ready or legacy_success) or errors > 0:
            ready = False
            reasons.append("METALS_PLATFORM_NOT_READY")
    return ready, sorted(set(reasons))


def _select_forecast(rows: list[dict[str, str]], horizon_months: int) -> dict[str, str] | None:
    if not rows:
        return None
    exact = [row for row in rows if int(_number(row.get("forecast_horizon_months"), -1)) == horizon_months]
    candidates = exact or rows
    return max(
        candidates,
        key=lambda row: (
            _number(row.get("forecast_horizon_months"), 0),
            _number(row.get("forecast_confidence"), 0),
        ),
    )


def build_metals_domain_package(
    package_root: Path,
    *,
    allocation_ceiling: float,
    minimum_deployment_score: float = 55.0,
    allocation_increment: float = 1.0,
    forecast_horizon_months: int = DEFAULT_FORECAST_HORIZON_MONTHS,
) -> dict[str, Any]:
    package_root = package_root.resolve()
    missing = [name for name in REQUIRED_FILES if not (package_root / name).is_file()]
    if missing:
        return {
            "schema_version": DOMAIN_SCHEMA_VERSION,
            "domain": "metals",
            "domain_status": "INCOMPLETE",
            "allocation_authority": "UIP",
            "scheduling_authority": "UIP",
            "domain_self_allocation_disabled": True,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "opportunity_count": 0,
            "deployable_opportunity_count": 0,
            "assigned_carry_forward": 0.0,
            "opportunities": [],
            "reason_codes": ["METALS_CERTIFIED_PACKAGE_INCOMPLETE"],
            "missing_files": missing,
        }

    assets = _read_csv(package_root / "asset_master.csv")
    forecasts = _read_csv(package_root / "forecasts.csv")
    recommendations = _read_csv(package_root / "recommendations.csv")
    risk_rows = _read_csv(package_root / "risk_metrics.csv")
    positions = _read_csv(package_root / "portfolio_positions.csv")
    platform_rows = _read_csv(package_root / "platform_status.csv")

    ready, status_reasons = _platform_ready(platform_rows)
    asset_by_id = {
        str(_first(row, "universal_asset_id", "asset_id", default="")).strip(): row
        for row in assets
        if str(_first(row, "universal_asset_id", "asset_id", default="")).strip()
    }
    forecasts_by_id: dict[str, list[dict[str, str]]] = {}
    for row in forecasts:
        asset_id = str(_first(row, "universal_asset_id", "asset_id", default="")).strip()
        if asset_id:
            forecasts_by_id.setdefault(asset_id, []).append(row)
    risk_by_id: dict[str, float] = {}
    for row in risk_rows:
        asset_id = str(_first(row, "universal_asset_id", "asset_id", default="")).strip()
        if asset_id:
            risk_by_id[asset_id] = max(risk_by_id.get(asset_id, 0.0), _number(row.get("risk_score")))
    position_by_id: dict[str, float] = {}
    for row in positions:
        asset_id = str(_first(row, "universal_asset_id", "asset_id", default="")).strip()
        if asset_id:
            position_by_id[asset_id] = position_by_id.get(asset_id, 0.0) + _number(
                _first(row, "position_value", "market_value", default=0)
            )

    opportunities: list[dict[str, Any]] = []
    for row in recommendations:
        asset_id = str(_first(row, "universal_asset_id", "asset_id", default="")).strip()
        if not asset_id:
            continue
        asset = asset_by_id.get(asset_id, {})
        score = max(0.0, min(100.0, _number(_first(row, "normalized_score", "score", default=0))))
        confidence = max(0.0, min(100.0, _number(_first(row, "confidence_score", "confidence", default=0))))
        forecast_asset_id = _forecast_asset_id(asset_id)
        selected_forecast = _select_forecast(forecasts_by_id.get(forecast_asset_id, []), forecast_horizon_months)
        expected_return = (
            _optional_number(_first(selected_forecast, "expected_total_return", "expected_return", "expected_return_pct", default=""))
            if selected_forecast
            else None
        )
        forecast_confidence = (
            _optional_number(_first(selected_forecast, "forecast_confidence", "confidence", default=""))
            if selected_forecast
            else None
        )
        signal = _normalized_signal(_first(row, "action", "recommendation", default=""), score, expected_return)
        target_weight_pct = max(0.0, _number(_first(row, "target_weight_pct", "target_weight", default=0)))
        recommended_amount = max(0.0, _number(_first(row, "recommended_dollars", "recommended_amount", default=0)))
        maximum = recommended_amount
        if maximum <= 0 and target_weight_pct > 0:
            maximum = allocation_ceiling * target_weight_pct / 100.0
        if maximum <= 0:
            maximum = allocation_ceiling
        maximum = round(min(maximum, allocation_ceiling), 2)
        increment = round(max(0.01, allocation_increment), 2)
        forecast_evidence_required = signal in DEPLOYABLE_SIGNALS
        eligible = bool(
            ready
            and signal in DEPLOYABLE_SIGNALS
            and score >= minimum_deployment_score
            and maximum >= increment
            and (not forecast_evidence_required or (expected_return is not None and expected_return > 0))
        )
        name = str(_first(asset, "asset_name", "name", "symbol", default=asset_id))
        evidence_reasons = ["CERTIFIED_METALS_RECOMMENDATION"]
        if selected_forecast:
            evidence_reasons.append("UNDERLYING_COMMODITY_FORECAST_LINKED")
        else:
            evidence_reasons.append("FORECAST_EVIDENCE_MISSING")
        if asset_id in position_by_id:
            evidence_reasons.append("PORTFOLIO_POSITION_RECONCILED")
        opportunities.append({
            "opportunity_id": str(_first(row, "recommendation_id", default=f"metals:{asset_id}")),
            "domain": "metals",
            "asset_class": "metals",
            "asset_id": asset_id,
            "name": name,
            "signal": signal,
            "eligible_for_new_capital": eligible,
            "allocation_score": round(score, 2),
            "confidence_score": round(confidence, 2),
            "minimum_allocation": increment,
            "allocation_increment": increment,
            "maximum_allocation": maximum,
            "whole_units_required": False,
            "expected_return": round(expected_return, 6) if expected_return is not None else None,
            "forecast_horizon_months": forecast_horizon_months if selected_forecast else None,
            "forecast_confidence": round(forecast_confidence, 4) if forecast_confidence is not None else None,
            "forecast_asset_id": forecast_asset_id if selected_forecast else None,
            "target_weight_pct": round(target_weight_pct, 4),
            "current_position_value": round(position_by_id.get(asset_id, 0.0), 2),
            "risk_score": round(risk_by_id.get(asset_id, 0.0), 2),
            "source_recommendation": str(_first(row, "action", "recommendation", default="")),
            "rationale": str(_first(row, "rationale_summary", "rationale", default="")),
            "source_system": str(row.get("source_system") or "metals-certified-adapter"),
            "source_run_id": str(_first(row, "source_run_id", "run_id", default="")),
            "evidence_reason_codes": evidence_reasons,
        })

    opportunities.sort(key=lambda item: (-float(item["allocation_score"]), -float(item["confidence_score"]), item["name"]))
    generated = str(_first(platform_rows[0], "run_completed_at_utc", "generated_at_utc", default="")) if platform_rows else ""
    generated = generated or datetime.now(timezone.utc).isoformat()
    domain_status = "PASS" if ready and opportunities else "INCOMPLETE"
    reasons = ["CERTIFIED_METALS_DOMAIN_ADAPTER_COMPLETED"] if domain_status == "PASS" else status_reasons or ["METALS_NO_RECOMMENDATIONS"]
    return {
        "schema_version": DOMAIN_SCHEMA_VERSION,
        "domain": "metals",
        "domain_status": domain_status,
        "allocation_authority": "UIP",
        "scheduling_authority": "UIP",
        "domain_self_allocation_disabled": True,
        "generated_at_utc": generated,
        "source_contract_version": "v1",
        "source_interface": "metals-certified-universal-adapter",
        "forecast_horizon_months": forecast_horizon_months,
        "opportunity_count": len(opportunities),
        "deployable_opportunity_count": sum(bool(item["eligible_for_new_capital"]) for item in opportunities),
        "assigned_carry_forward": 0.0,
        "opportunities": opportunities,
        "reason_codes": reasons,
    }


def write_metals_domain_package(
    package_root: Path,
    output_path: Path,
    *,
    allocation_ceiling: float,
    minimum_deployment_score: float = 55.0,
    allocation_increment: float = 1.0,
    forecast_horizon_months: int = DEFAULT_FORECAST_HORIZON_MONTHS,
) -> dict[str, Any]:
    payload = build_metals_domain_package(
        package_root,
        allocation_ceiling=allocation_ceiling,
        minimum_deployment_score=minimum_deployment_score,
        allocation_increment=allocation_increment,
        forecast_horizon_months=forecast_horizon_months,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import shutil
import uuid

import pandas as pd

from .config import AdapterConfig, load_config
from .contracts import Contract, load_contract
from .native_surfaces import load_bridge_surface

CONTRACTS = (
    "asset_master",
    "forecasts",
    "recommendations",
    "risk_metrics",
    "portfolio_positions",
    "platform_status",
    "export_manifest",
)
SUPPORTING_NATIVE_FILES = (
    "latest_forecast_model_components.csv",
    "latest_learned_regime_probabilities.csv",
    "latest_uncertainty_adjusted_views.csv",
    "latest_recommendation_change_explanations.csv",
    "latest_data_freshness_details.csv",
    "latest_platform_health_score.csv",
    "latest_monthly_committee_report.csv",
)


@dataclass(frozen=True)
class BuildContext:
    universal_root: Path
    metals_root: Path
    output_root: Path
    schema_root: Path
    config: AdapterConfig
    package_id: str
    generated_at_utc: str
    allow_legacy_database_fallback: bool = False


def _first(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and not (isinstance(value, float) and pd.isna(value)) and str(value) != "":
            return value
    return default


def _asset_id(config: AdapterConfig, asset: str, kind: str = "metal") -> str:
    key = str(asset).strip().lower()
    configured = config.asset_crosswalk.get(key, {}).get("asset_id")
    return configured or f"metals:{kind}:{key}"


def _symbol(config: AdapterConfig, asset: str) -> str:
    key = str(asset).strip().lower()
    return config.asset_crosswalk.get(key, {}).get("symbol", str(asset).upper())


def _records_to_contract(records: list[dict[str, Any]], contract: Contract) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    for column in contract.columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[contract.columns]


def _read_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required Metals native export not found: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_contracts(ctx: BuildContext) -> dict[str, Contract]:
    loaded = {}
    for name in CONTRACTS:
        candidates = [
            ctx.schema_root / f"{name}_columns.csv",
            ctx.schema_root / f"{name}.csv",
            ctx.schema_root / f"{name}_schema.csv",
            ctx.schema_root / f"{name}_definition.csv",
        ]
        selected = next((path for path in candidates if path.exists()), candidates[0])
        loaded[name] = load_contract(selected)
    return loaded



def _coalesce_series(frame: pd.DataFrame, *columns: str, default: Any = pd.NA) -> pd.Series:
    result = pd.Series(default, index=frame.index, dtype="object")
    for column in columns:
        if column in frame.columns:
            candidate = frame[column]
            mask = result.isna() | result.astype(str).str.strip().eq("")
            result.loc[mask] = candidate.loc[mask]
    return result


def _risk_level(score: object) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if value < 25:
        return "LOW"
    if value < 50:
        return "MODERATE"
    if value < 75:
        return "HIGH"
    return "VERY_HIGH"


def _apply_universal_aliases(name: str, frame: pd.DataFrame, ctx: BuildContext) -> pd.DataFrame:
    """Populate canonical Phase 0 field names from Metals-native aliases."""
    frame = frame.copy()
    if frame.empty:
        return frame

    if "run_id" in frame.columns:
        frame["run_id"] = _coalesce_series(
            frame, "run_id", "source_run_id", "forecast_run_id",
            "risk_run_id", "decision_run_id", default=ctx.package_id
        ).fillna(ctx.package_id)

    if "universal_asset_id" in frame.columns:
        frame["universal_asset_id"] = _coalesce_series(
            frame, "universal_asset_id", "asset_id"
        )

    if name == "asset_master":
        if "platform_asset_id" in frame.columns:
            frame["platform_asset_id"] = _coalesce_series(
                frame, "platform_asset_id", "native_id", "symbol", "ticker", "asset_id"
            )
        if "investable" in frame.columns:
            frame["investable"] = _coalesce_series(frame, "investable", "is_active", default=True).fillna(True)
        if "last_updated_at_utc" in frame.columns:
            frame["last_updated_at_utc"] = _coalesce_series(
                frame, "last_updated_at_utc", "updated_at_utc", "generated_at_utc",
                default=ctx.generated_at_utc
            ).fillna(ctx.generated_at_utc)

    elif name == "forecasts":
        if "forecast_origin_date" in frame.columns:
            frame["forecast_origin_date"] = _coalesce_series(
                frame, "forecast_origin_date", "forecast_date", "as_of_date",
                default=ctx.generated_at_utc[:10]
            ).fillna(ctx.generated_at_utc[:10])
        if "forecast_horizon_months" in frame.columns:
            frame["forecast_horizon_months"] = pd.to_numeric(
                _coalesce_series(frame, "forecast_horizon_months", "horizon_months"), errors="coerce"
            )
        if "forecast_method" in frame.columns:
            frame["forecast_method"] = _coalesce_series(
                frame, "forecast_method", default="metals_native_v8_ensemble"
            ).fillna("metals_native_v8_ensemble")

    elif name == "recommendations":
        if "normalized_score" in frame.columns:
            frame["normalized_score"] = pd.to_numeric(
                _coalesce_series(frame, "normalized_score", "score", "confidence"), errors="coerce"
            ).clip(lower=0, upper=100)
        if "confidence_score" in frame.columns:
            frame["confidence_score"] = pd.to_numeric(
                _coalesce_series(frame, "confidence_score", "confidence", "score"), errors="coerce"
            ).clip(lower=0, upper=100)

    elif name == "risk_metrics":
        if "risk_score" in frame.columns:
            raw = pd.to_numeric(
                _coalesce_series(
                    frame, "risk_score", "component_risk_pct", "volatility",
                    "portfolio_volatility", "value_at_risk", "var"
                ), errors="coerce"
            )
            # Native volatility/VaR values may be decimals; convert those to a 0-100 scale.
            frame["risk_score"] = raw.where(raw.abs() > 1, raw.abs() * 100).abs().clip(lower=0, upper=100)
        if "risk_level" in frame.columns:
            existing = _coalesce_series(frame, "risk_level")
            derived = frame["risk_score"].map(_risk_level) if "risk_score" in frame.columns else "UNKNOWN"
            frame["risk_level"] = existing.where(~(existing.isna() | existing.astype(str).str.strip().eq("")), derived)

    elif name == "portfolio_positions":
        if "position_value" in frame.columns:
            frame["position_value"] = pd.to_numeric(
                _coalesce_series(frame, "position_value", "market_value"), errors="coerce"
            )
        if "current_weight" in frame.columns:
            existing = pd.to_numeric(_coalesce_series(frame, "current_weight"), errors="coerce")
            values = pd.to_numeric(frame.get("position_value", pd.Series(index=frame.index, dtype=float)), errors="coerce")
            total = values.sum(min_count=1)
            derived = values / total if pd.notna(total) and total != 0 else pd.Series(0.0, index=frame.index)
            frame["current_weight"] = existing.fillna(derived)
        if "last_updated_at_utc" in frame.columns:
            frame["last_updated_at_utc"] = _coalesce_series(
                frame, "last_updated_at_utc", "generated_at_utc",
                default=ctx.generated_at_utc
            ).fillna(ctx.generated_at_utc)

    elif name == "platform_status":
        if "run_started_at_utc" in frame.columns:
            frame["run_started_at_utc"] = _coalesce_series(
                frame, "run_started_at_utc", "generated_at_utc",
                default=ctx.generated_at_utc
            ).fillna(ctx.generated_at_utc)
        if "data_as_of_date" in frame.columns:
            frame["data_as_of_date"] = _coalesce_series(
                frame, "data_as_of_date", "as_of_date", default=ctx.generated_at_utc[:10]
            ).fillna(ctx.generated_at_utc[:10])
        if "warning_count" in frame.columns:
            frame["warning_count"] = pd.to_numeric(
                _coalesce_series(frame, "warning_count", "freshness_failures", default=0), errors="coerce"
            ).fillna(0).astype(int)
        if "error_count" in frame.columns:
            frame["error_count"] = pd.to_numeric(
                _coalesce_series(frame, "error_count", default=0), errors="coerce"
            ).fillna(0).astype(int)

    return frame

def _asset_master(ctx: BuildContext, contract: Contract, exports: Path, database: Path) -> pd.DataFrame:
    forecasts = _read_csv(exports / "latest_metal_forecasts.csv")
    rankings = _read_csv(exports / "latest_metal_opportunity_rankings.csv")
    vehicles = load_bridge_surface(exports, "vehicle_recommendations", database=database, allow_legacy_database_fallback=ctx.allow_legacy_database_fallback)
    metal_names = sorted(set(forecasts.get("metal", pd.Series(dtype=str)).dropna().astype(str)) | set(rankings.get("metal", pd.Series(dtype=str)).dropna().astype(str)))
    records: list[dict[str, Any]] = []
    for metal in metal_names:
        records.append({
            "asset_id": _asset_id(ctx.config, metal), "universal_asset_id": _asset_id(ctx.config, metal),
            "platform_asset_id": metal.lower(), "platform_id": ctx.config.platform_id,
            "asset_class": "metals", "asset_type": "commodity", "symbol": _symbol(ctx.config, metal),
            "asset_name": metal.title(), "name": metal.title(), "native_id": metal.lower(),
            "currency": ctx.config.currency, "is_active": True, "status": "active",
            "source_system": ctx.config.source_interface, "contract_version": ctx.config.contract_version,
            "as_of_date": ctx.generated_at_utc[:10], "updated_at_utc": ctx.generated_at_utc,
        })
    for _, row in vehicles.iterrows():
        r = row.to_dict(); ticker = str(r.get("ticker", "")).strip()
        if not ticker: continue
        records.append({
            "asset_id": _asset_id(ctx.config, ticker, "vehicle"), "universal_asset_id": _asset_id(ctx.config, ticker, "vehicle"),
            "platform_asset_id": ticker, "platform_id": ctx.config.platform_id,
            "asset_class": "metals", "asset_type": str(r.get("vehicle_type", "investment_vehicle")),
            "symbol": ticker, "ticker": ticker, "asset_name": ticker, "name": ticker,
            "native_id": ticker, "parent_asset_id": _asset_id(ctx.config, str(r.get("metal", "unknown"))),
            "currency": ctx.config.currency, "is_active": True, "status": "active",
            "source_system": ctx.config.source_interface, "contract_version": ctx.config.contract_version,
            "as_of_date": ctx.generated_at_utc[:10], "updated_at_utc": ctx.generated_at_utc,
        })
    return _records_to_contract(records, contract).drop_duplicates(subset=[c for c in ["asset_id"] if c in contract.columns] or None)


def _forecasts(ctx: BuildContext, contract: Contract, exports: Path) -> pd.DataFrame:
    native = _read_csv(exports / "latest_metal_forecasts.csv")
    records=[]
    for _, row in native.iterrows():
        r=row.to_dict(); metal=str(r.get("metal", "")); horizon=int(r.get("horizon_months", 0))
        records.append({
            "forecast_id": f"metals:{r.get('forecast_run_id')}:{metal}:{horizon}m",
            "platform_id": ctx.config.platform_id, "asset_id": _asset_id(ctx.config, metal),
            "universal_asset_id": _asset_id(ctx.config, metal),
            "forecast_run_id": r.get("forecast_run_id"), "as_of_date": ctx.generated_at_utc[:10],
            "forecast_date": ctx.generated_at_utc[:10], "horizon": f"{horizon}m", "horizon_months": horizon,
            "forecast_horizon_months": horizon,
            "expected_return": r.get("expected_return"), "expected_return_pct": r.get("expected_return"),
            "lower_bound": r.get("lower_bound"), "upper_bound": r.get("upper_bound"),
            "forecast_volatility": r.get("forecast_volatility"), "volatility": r.get("forecast_volatility"),
            "downside_probability": r.get("downside_probability"), "dominant_regime": r.get("dominant_regime"),
            "model_agreement": r.get("model_agreement"), "confidence": r.get("model_agreement"),
            "return_unit": "decimal", "currency": ctx.config.currency,
            "source_system": ctx.config.source_interface, "contract_version": ctx.config.contract_version,
            "generated_at_utc": ctx.generated_at_utc,
        })
    return _records_to_contract(records, contract)


def _recommendations(ctx: BuildContext, contract: Contract, exports: Path, database: Path) -> pd.DataFrame:
    opportunities = _read_csv(exports / "latest_metal_opportunity_rankings.csv")
    history = load_bridge_surface(exports, "recommendation_history", database=database, allow_legacy_database_fallback=ctx.allow_legacy_database_fallback)
    records=[]
    for _, row in opportunities.iterrows():
        r=row.to_dict(); metal=str(r.get("metal", "")); run=r.get("decision_run_id")
        records.append({
            "recommendation_id": f"metals:{run}:metal:{metal}", "platform_id": ctx.config.platform_id,
            "asset_id": _asset_id(ctx.config, metal), "universal_asset_id": _asset_id(ctx.config, metal),
            "as_of_date": ctx.generated_at_utc[:10],
            "recommendation_date": ctx.generated_at_utc[:10], "recommendation": "RANKED_OPPORTUNITY",
            "action": "RANKED_OPPORTUNITY", "rank": r.get("opportunity_rank"),
            "target_weight": r.get("target_weight_pct"), "target_weight_pct": r.get("target_weight_pct"),
            "expected_return": r.get("expected_return"), "confidence": r.get("average_confidence"),
            "score": r.get("opportunity_score"), "normalized_score": _first(r, "opportunity_score", "average_confidence", default=50),
            "confidence_score": _first(r, "average_confidence", "opportunity_score", default=50),
            "rationale": r.get("rationale"),
            "source_run_id": run, "source_system": ctx.config.source_interface,
            "contract_version": ctx.config.contract_version, "generated_at_utc": ctx.generated_at_utc,
        })
    for _, row in history.iterrows():
        r=row.to_dict(); ticker=str(r.get("ticker", "")); run=r.get("decision_run_id")
        records.append({
            "recommendation_id": f"metals:{run}:vehicle:{ticker}", "platform_id": ctx.config.platform_id,
            "asset_id": _asset_id(ctx.config, ticker, "vehicle"), "universal_asset_id": _asset_id(ctx.config, ticker, "vehicle"),
            "as_of_date": r.get("recommendation_date"),
            "recommendation_date": r.get("recommendation_date"), "recommendation": r.get("action"),
            "action": r.get("action"), "recommended_amount": r.get("recommended_dollars"),
            "recommended_dollars": r.get("recommended_dollars"), "target_weight": r.get("target_weight_pct"),
            "target_weight_pct": r.get("target_weight_pct"), "confidence": r.get("confidence"),
            "normalized_score": _first(r, "score", "confidence", default=50),
            "confidence_score": _first(r, "confidence", "score", default=50),
            "rationale": r.get("explanation"), "source_run_id": run,
            "source_system": ctx.config.source_interface, "contract_version": ctx.config.contract_version,
            "generated_at_utc": ctx.generated_at_utc,
        })
    return _records_to_contract(records, contract)


def _risk_metrics(ctx: BuildContext, contract: Contract, exports: Path, database: Path) -> pd.DataFrame:
    portfolio = load_bridge_surface(exports, "portfolio_risk_metrics", database=database, allow_legacy_database_fallback=ctx.allow_legacy_database_fallback)
    contributions = load_bridge_surface(exports, "risk_contributions", database=database, allow_legacy_database_fallback=ctx.allow_legacy_database_fallback)
    records=[]
    for _, row in portfolio.iterrows():
        r=row.to_dict(); run=r.get("risk_run_id")
        base={
            "risk_metric_id": f"metals:{run}:portfolio", "platform_id": ctx.config.platform_id,
            "portfolio_id": ctx.config.portfolio_id, "asset_id": f"metals:portfolio:{ctx.config.portfolio_id}",
            "universal_asset_id": f"metals:portfolio:{ctx.config.portfolio_id}", "as_of_date": r.get("as_of_date"),
            "risk_run_id": run, "portfolio_volatility": r.get("portfolio_volatility"),
            "risk_score": abs(float(r.get("portfolio_volatility") or 0)) * 100,
            "volatility": r.get("portfolio_volatility"), "value_at_risk": r.get("value_at_risk"),
            "var": r.get("value_at_risk"), "conditional_value_at_risk": r.get("conditional_value_at_risk"),
            "cvar": r.get("conditional_value_at_risk"), "max_drawdown": r.get("max_drawdown"),
            "beta": r.get("beta_to_gold"), "beta_to_gold": r.get("beta_to_gold"),
            "diversification_ratio": r.get("diversification_ratio"), "concentration_hhi": r.get("concentration_hhi"),
            "source_system": ctx.config.source_interface, "source_run_id": run,
            "contract_version": ctx.config.contract_version, "generated_at_utc": ctx.generated_at_utc,
        }
        records.append(base)
    for _, row in contributions.iterrows():
        r=row.to_dict(); ticker=str(r.get("ticker", "")); run=r.get("risk_run_id")
        records.append({
            "risk_metric_id": f"metals:{run}:vehicle:{ticker}", "platform_id": ctx.config.platform_id,
            "portfolio_id": ctx.config.portfolio_id, "asset_id": _asset_id(ctx.config, ticker, "vehicle"),
            "universal_asset_id": _asset_id(ctx.config, ticker, "vehicle"),
            "as_of_date": portfolio.iloc[0].get("as_of_date") if not portfolio.empty else ctx.generated_at_utc[:10],
            "risk_run_id": run, "portfolio_weight": r.get("portfolio_weight_pct"),
            "portfolio_weight_pct": r.get("portfolio_weight_pct"), "volatility": r.get("volatility"),
            "marginal_risk": r.get("marginal_risk"), "component_risk": r.get("component_risk"),
            "component_risk_pct": r.get("component_risk_pct"),
            "risk_score": abs(float(_first(r, "component_risk_pct", "volatility", default=0) or 0)) * (1 if abs(float(_first(r, "component_risk_pct", "volatility", default=0) or 0)) > 1 else 100),
            "source_system": ctx.config.source_interface,
            "source_run_id": run, "contract_version": ctx.config.contract_version,
            "generated_at_utc": ctx.generated_at_utc,
        })
    return _records_to_contract(records, contract)


def _positions(ctx: BuildContext, contract: Contract, database: Path) -> pd.DataFrame:
    native=load_bridge_surface(ctx.metals_root / "data" / "exports", "portfolio_positions", database=database, allow_legacy_database_fallback=ctx.allow_legacy_database_fallback)
    records=[]
    for _, row in native.iterrows():
        r=row.to_dict(); ticker=str(r.get("ticker", "")); run=r.get("portfolio_run_id")
        records.append({
            "position_id": f"metals:{run}:{r.get('account_name')}:{ticker}", "platform_id": ctx.config.platform_id,
            "portfolio_id": ctx.config.portfolio_id, "account_id": r.get("account_name") or ctx.config.account_id,
            "account_name": r.get("account_name"), "account_type": r.get("account_type"),
            "asset_id": _asset_id(ctx.config, ticker, "vehicle"), "universal_asset_id": _asset_id(ctx.config, ticker, "vehicle"),
            "ticker": ticker,
            "quantity": r.get("shares"), "shares": r.get("shares"), "current_price": r.get("current_price"),
            "market_value": r.get("market_value"), "position_value": _first(r, "market_value", "total_cost_basis", default=0),
            "cost_basis_per_unit": r.get("cost_basis_per_share"),
            "cost_basis_per_share": r.get("cost_basis_per_share"), "total_cost_basis": r.get("total_cost_basis"),
            "unrealized_gain_loss": r.get("unrealized_gain_loss"), "holding_days": r.get("holding_days"),
            "currency": ctx.config.currency, "as_of_date": ctx.generated_at_utc[:10],
            "source_run_id": run, "source_system": ctx.config.source_interface,
            "contract_version": ctx.config.contract_version, "generated_at_utc": ctx.generated_at_utc,
        })
    return _records_to_contract(records, contract)


def _platform_status(ctx: BuildContext, contract: Contract, exports: Path) -> pd.DataFrame:
    health=_read_csv(exports / "latest_platform_health_score.csv")
    freshness=_read_csv(exports / "latest_data_freshness_details.csv")
    h=health.iloc[0].to_dict() if not health.empty else {}
    failed=int((freshness.get("freshness_status", pd.Series(dtype=str)).astype(str).str.upper() != "PASS").sum()) if not freshness.empty else 0
    oldest=float(pd.to_numeric(freshness.get("age_days", pd.Series(dtype=float)), errors="coerce").max()) if not freshness.empty else float("nan")
    status="READY" if failed == 0 and (pd.isna(oldest) or oldest <= ctx.config.stale_after_days) else "DEGRADED"
    record={
        "platform_status_id": f"metals:{h.get('decision_run_id', ctx.package_id)}", "platform_id": ctx.config.platform_id,
        "platform_name": "Metals Intelligence Platform", "platform_version": "v8.1",
        "source_interface": ctx.config.source_interface, "status": status, "run_status": "SUCCESS",
        "as_of_date": ctx.generated_at_utc[:10], "decision_run_id": h.get("decision_run_id"),
        "data_freshness_score": h.get("data_freshness_score"), "model_confidence_score": h.get("model_confidence_score"),
        "recommendation_quality_score": h.get("recommendation_quality_score"),
        "pipeline_completeness_score": h.get("pipeline_completeness_score"),
        "overall_health_score": h.get("overall_platform_health"), "platform_grade": h.get("platform_grade"),
        "freshness_failures": failed, "oldest_source_age_days": oldest, "validation_status": "PENDING_PACKAGE_VALIDATION",
        "message": h.get("explanation"), "source_system": ctx.config.source_interface,
        "contract_version": ctx.config.contract_version, "generated_at_utc": ctx.generated_at_utc,
    }
    return _records_to_contract([record], contract)


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_frame(frame: pd.DataFrame, contract: Contract) -> list[str]:
    issues=[]
    missing=[column for column in contract.columns if column not in frame.columns]
    if missing: issues.append(f"missing columns: {missing}")
    for column in contract.required_columns:
        if column in frame.columns and (frame[column].isna() | frame[column].astype(str).str.strip().eq("")).any():
            issues.append(f"required column contains null/blank values: {column}")
    return issues


def build_package(universal_root: Path, metals_root: Path, output_root: Path | None = None,
                  config_path: Path | None = None, schema_root: Path | None = None,
                  allow_legacy_database_fallback: bool = False) -> Path:
    universal_root=universal_root.resolve(); metals_root=metals_root.resolve()
    generated=datetime.now(timezone.utc); package_id=f"metals-{generated.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output_root=(output_root or universal_root / "data" / "integration" / "metals").resolve()
    package_dir=output_root / package_id
    schema_root=(schema_root or universal_root / "schemas" / "v1" / "csv").resolve()
    config_path=(config_path or universal_root / "exchange" / "metals" / "config" / "adapter_config.json").resolve()
    ctx=BuildContext(universal_root, metals_root, output_root, schema_root, load_config(config_path), package_id, generated.isoformat(), allow_legacy_database_fallback)
    contracts=_load_contracts(ctx); exports=metals_root / "data" / "exports"; database=metals_root / "data" / "metals_intelligence.duckdb"
    package_dir.mkdir(parents=True, exist_ok=False); support_dir=package_dir / "supporting_native"; support_dir.mkdir()
    frames={
        "asset_master": _asset_master(ctx, contracts["asset_master"], exports, database),
        "forecasts": _forecasts(ctx, contracts["forecasts"], exports),
        "recommendations": _recommendations(ctx, contracts["recommendations"], exports, database),
        "risk_metrics": _risk_metrics(ctx, contracts["risk_metrics"], exports, database),
        "portfolio_positions": _positions(ctx, contracts["portfolio_positions"], database),
        "platform_status": _platform_status(ctx, contracts["platform_status"], exports),
    }
    frames = {name: _apply_universal_aliases(name, frame, ctx) for name, frame in frames.items()}
    published_count = sum(len(frame) for name, frame in frames.items() if name != "platform_status")
    if "records_published" in frames["platform_status"].columns:
        frames["platform_status"]["records_published"] = published_count
    validation={}; written=[]
    for name, frame in frames.items():
        path=package_dir / f"{name}.csv"; frame.to_csv(path,index=False); written.append(path)
        validation[name]=_validate_frame(frame, contracts[name])
    for filename in SUPPORTING_NATIVE_FILES:
        source=exports / filename
        if source.exists(): shutil.copy2(source, support_dir / filename)
    manifest_records=[]
    for path in sorted(package_dir.rglob("*")):
        if path.is_file() and path.name != "export_manifest.csv":
            rows=-1
            if path.suffix.lower()==".csv":
                try: rows=len(pd.read_csv(path))
                except Exception: rows=-1
            name=path.stem
            issues=validation.get(name, [])
            manifest_records.append({
                "manifest_id": f"{package_id}:{path.relative_to(package_dir).as_posix()}", "package_id": package_id,
                "platform_id": ctx.config.platform_id, "file_name": path.name,
                "relative_path": path.relative_to(package_dir).as_posix(), "dataset_name": name,
                "row_count": rows, "sha256": _sha256(path), "source_interface": ctx.config.source_interface,
                "contract_version": ctx.config.contract_version, "generated_at_utc": ctx.generated_at_utc,
                "validation_status": "PASS" if not issues else "FAIL", "validation_message": "; ".join(issues),
            })
    manifest=_records_to_contract(manifest_records, contracts["export_manifest"])
    manifest_path=package_dir / "export_manifest.csv"; manifest.to_csv(manifest_path,index=False)
    all_issues=[f"{name}: {issue}" for name,issues in validation.items() for issue in issues]
    summary={"package_id":package_id,"platform_id":ctx.config.platform_id,"source_interface":ctx.config.source_interface,
             "contract_version":ctx.config.contract_version,"generated_at_utc":ctx.generated_at_utc,
             "validation_status":"PASS" if not all_issues else "FAIL","issues":all_issues,
             "files":[p.relative_to(package_dir).as_posix() for p in package_dir.rglob('*') if p.is_file()]}
    (package_dir / "package_summary.json").write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    latest=output_root / "latest"
    if latest.exists() or latest.is_symlink():
        if latest.is_dir(): shutil.rmtree(latest)
        else: latest.unlink()
    shutil.copytree(package_dir, latest)
    if all_issues:
        raise RuntimeError("Universal package created but contract validation failed: " + " | ".join(all_issues))
    return package_dir

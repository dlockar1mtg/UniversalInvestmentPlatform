"""Semantic parity checks for Metals v8 model evidence and universal exports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


class MetalsParityError(RuntimeError):
    """Raised when Metals source evidence or universal transformation drifts."""


@dataclass(frozen=True)
class ParityCheck:
    name: str
    records: int
    detail: str


def _require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise MetalsParityError(f"{name} is missing columns: {missing}")


def _unique(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    if frame.duplicated(columns).any():
        raise MetalsParityError(f"{name} contains duplicate keys: {columns}")


def _close(left: pd.Series, right: pd.Series, tolerance: float = 1e-10) -> bool:
    first = pd.to_numeric(left, errors="coerce")
    second = pd.to_numeric(right, errors="coerce")
    return bool(((first - second).abs() <= tolerance).all())


def validate_model_evidence(
    forecasts: pd.DataFrame,
    components: pd.DataFrame,
    regimes: pd.DataFrame,
    adjusted_views: pd.DataFrame,
) -> tuple[ParityCheck, ...]:
    forecast_key = ["metal", "horizon_months"]
    _require_columns(
        forecasts,
        {"forecast_run_id", "metal", "horizon_months", "expected_return"},
        "metal forecasts",
    )
    _require_columns(
        components,
        {
            "forecast_run_id", "metal", "horizon_months", "model_name",
            "model_forecast", "model_weight",
        },
        "forecast model components",
    )
    _require_columns(
        regimes,
        {"forecast_run_id", "metal", "regime", "probability"},
        "learned regime probabilities",
    )
    _require_columns(
        adjusted_views,
        {
            "forecast_run_id", "ticker", "metal", "horizon_months",
            "raw_expected_return", "uncertainty_penalty", "downside_penalty",
            "adjusted_expected_return",
        },
        "uncertainty-adjusted views",
    )
    _unique(forecasts, forecast_key, "metal forecasts")
    _unique(components, forecast_key + ["model_name"], "forecast model components")
    _unique(regimes, ["metal", "regime"], "learned regime probabilities")
    _unique(adjusted_views, ["ticker", "horizon_months"], "uncertainty-adjusted views")

    run_ids = set(forecasts["forecast_run_id"].astype(str))
    for name, frame in (
        ("forecast model components", components),
        ("learned regime probabilities", regimes),
        ("uncertainty-adjusted views", adjusted_views),
    ):
        if set(frame["forecast_run_id"].astype(str)) != run_ids:
            raise MetalsParityError(f"{name} does not share the certified forecast run")

    forecast_keys = set(map(tuple, forecasts[forecast_key].astype(str).to_numpy()))
    component_keys = set(map(tuple, components[forecast_key].astype(str).to_numpy()))
    if component_keys != forecast_keys:
        raise MetalsParityError("model-component coverage does not match forecast keys")
    component_counts = components.groupby(forecast_key).size()
    if (component_counts < 2).any():
        raise MetalsParityError("each forecast must contain at least two model components")
    weight_sums = components.groupby(forecast_key)["model_weight"].sum()
    if not ((pd.to_numeric(weight_sums, errors="coerce") - 1.0).abs() <= 1e-10).all():
        raise MetalsParityError("model weights do not sum to one for every forecast")

    probabilities = pd.to_numeric(regimes["probability"], errors="coerce")
    if probabilities.isna().any() or ((probabilities < 0) | (probabilities > 1)).any():
        raise MetalsParityError("regime probabilities must be numeric values between zero and one")
    probability_sums = regimes.assign(probability=probabilities).groupby("metal")["probability"].sum()
    if not ((probability_sums - 1.0).abs() <= 1e-10).all():
        raise MetalsParityError("regime probabilities do not sum to one for every metal")
    if set(regimes["metal"].astype(str)) != set(forecasts["metal"].astype(str)):
        raise MetalsParityError("regime probability metals do not match forecast metals")

    adjusted_keys = set(map(tuple, adjusted_views[forecast_key].astype(str).to_numpy()))
    if not adjusted_keys <= forecast_keys:
        raise MetalsParityError("uncertainty-adjusted views contain orphan forecast keys")
    expected_adjusted = (
        pd.to_numeric(adjusted_views["raw_expected_return"], errors="coerce")
        - pd.to_numeric(adjusted_views["uncertainty_penalty"], errors="coerce")
        - pd.to_numeric(adjusted_views["downside_penalty"], errors="coerce")
    )
    if not _close(expected_adjusted, adjusted_views["adjusted_expected_return"]):
        raise MetalsParityError("uncertainty-adjusted return arithmetic does not reconcile")

    return (
        ParityCheck("forecast_keys", len(forecasts), "unique forecast keys"),
        ParityCheck("model_components", len(components), "complete multi-model coverage and normalized weights"),
        ParityCheck("regime_probabilities", len(regimes), "bounded and normalized by metal"),
        ParityCheck("uncertainty_adjustments", len(adjusted_views), "penalty arithmetic reconciles"),
    )


def certify_metals_parity(
    metals_root: str | Path,
    package_root: str | Path,
) -> dict:
    exports = Path(metals_root) / "data" / "exports"
    package = Path(package_root)
    native = {
        "forecasts": pd.read_csv(exports / "latest_metal_forecasts.csv"),
        "components": pd.read_csv(exports / "latest_forecast_model_components.csv"),
        "regimes": pd.read_csv(exports / "latest_learned_regime_probabilities.csv"),
        "adjusted": pd.read_csv(exports / "latest_uncertainty_adjusted_views.csv"),
        "opportunities": pd.read_csv(exports / "latest_metal_opportunity_rankings.csv"),
        "positions": pd.read_csv(exports / "latest_portfolio_positions.csv"),
        "portfolio_risk": pd.read_csv(exports / "latest_portfolio_risk_metrics.csv"),
        "risk_contributions": pd.read_csv(exports / "latest_risk_contributions.csv"),
    }
    universal = {
        "forecasts": pd.read_csv(package / "forecasts.csv"),
        "recommendations": pd.read_csv(package / "recommendations.csv"),
        "positions": pd.read_csv(package / "portfolio_positions.csv"),
        "risk": pd.read_csv(package / "risk_metrics.csv"),
    }
    summary = json.loads((package / "package_summary.json").read_text(encoding="utf-8"))
    if summary.get("validation_status") != "PASS":
        raise MetalsParityError("universal package validation status is not PASS")

    checks = list(
        validate_model_evidence(
            native["forecasts"],
            native["components"],
            native["regimes"],
            native["adjusted"],
        )
    )

    source_forecasts = native["forecasts"].copy()
    source_forecasts["universal_asset_id"] = (
        "metals:commodity:" + source_forecasts["metal"].astype(str).str.lower()
    )
    target_forecasts = universal["forecasts"]
    _require_columns(
        target_forecasts,
        {"universal_asset_id", "forecast_horizon_months", "expected_total_return"},
        "universal forecasts",
    )
    merged = source_forecasts.merge(
        target_forecasts,
        left_on=["universal_asset_id", "horizon_months"],
        right_on=["universal_asset_id", "forecast_horizon_months"],
        suffixes=("_native", "_universal"),
        how="outer",
        indicator=True,
    )
    if len(merged) != len(source_forecasts) or not merged["_merge"].eq("both").all():
        raise MetalsParityError("universal forecast keys do not match native forecasts")
    if not _close(merged["expected_return"], merged["expected_total_return"]):
        raise MetalsParityError("forecast transformation drift: expected_total_return")
    if "probability_positive_return" in merged:
        expected_probability = 1.0 - pd.to_numeric(
            merged["downside_probability"], errors="coerce"
        )
        if not _close(expected_probability, merged["probability_positive_return"]):
            raise MetalsParityError("forecast transformation drift: probability_positive_return")
    if "forecast_confidence" in merged:
        if not _close(merged["model_agreement"], merged["forecast_confidence"]):
            raise MetalsParityError("forecast transformation drift: forecast_confidence")
    checks.append(
        ParityCheck(
            "forecast_transformation",
            len(merged),
            "keys, total returns, probabilities, and confidence preserved",
        )
    )

    opportunity_assets = {
        f"metals:commodity:{metal.lower()}"
        for metal in native["opportunities"]["metal"].dropna().astype(str)
    }
    recommendations = universal["recommendations"]
    _require_columns(recommendations, {"universal_asset_id"}, "universal recommendations")
    recommendation_assets = set(recommendations["universal_asset_id"].astype(str))
    if not opportunity_assets <= recommendation_assets:
        raise MetalsParityError("native opportunity assets are missing from universal recommendations")
    checks.append(ParityCheck("recommendation_identity", len(opportunity_assets), "opportunity assets preserved"))

    source_positions = native["positions"].copy()
    target_positions = universal["positions"]
    _require_columns(source_positions, {"ticker", "shares"}, "native portfolio positions")
    _require_columns(
        target_positions,
        {"universal_asset_id", "quantity", "position_value"},
        "universal portfolio positions",
    )
    source_positions["universal_asset_id"] = (
        "metals:vehicle:" + source_positions["ticker"].astype(str).str.upper()
    )
    positions = source_positions.merge(
        target_positions,
        on="universal_asset_id",
        suffixes=("_native", "_universal"),
        how="outer",
        indicator=True,
    )
    if len(positions) != len(source_positions) or not positions["_merge"].eq("both").all():
        raise MetalsParityError("universal position asset identifiers do not match native tickers")
    if not _close(positions["shares"], positions["quantity"]):
        raise MetalsParityError("position quantities changed during transformation")
    if "market_value" in positions and not _close(
        positions["market_value"], positions["position_value"]
    ):
        raise MetalsParityError("position values changed during transformation")
    checks.append(
        ParityCheck(
            "portfolio_positions",
            len(positions),
            "canonical vehicle identifiers, quantities, and values preserved",
        )
    )

    expected_risk_rows = len(native["portfolio_risk"]) + len(native["risk_contributions"])
    if len(universal["risk"]) != expected_risk_rows:
        raise MetalsParityError("universal risk row count does not preserve native risk surfaces")
    checks.append(ParityCheck("risk_surface", expected_risk_rows, "portfolio and contribution rows preserved"))

    required_support = {
        "latest_forecast_model_components.csv",
        "latest_learned_regime_probabilities.csv",
        "latest_uncertainty_adjusted_views.csv",
        "latest_recommendation_change_explanations.csv",
        "latest_data_freshness_details.csv",
        "latest_platform_health_score.csv",
        "latest_monthly_committee_report.csv",
    }
    support = package / "supporting_native"
    missing_support = sorted(name for name in required_support if not (support / name).is_file())
    if missing_support:
        raise MetalsParityError(f"universal package is missing model evidence: {missing_support}")
    checks.append(ParityCheck("supporting_evidence", len(required_support), "all certified evidence retained"))

    return {
        "status": "PASS",
        "package_id": summary.get("package_id"),
        "checks": [
            {"name": item.name, "records": item.records, "detail": item.detail}
            for item in checks
        ],
    }

"""Metals out-of-sample forecast and recommendation outcome tracking."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping


@dataclass(frozen=True)
class MetalsOutcomeObservation:
    forecast_id: str
    asset_id: str
    vehicle_ticker: str
    horizon_days: int
    forecast_return_pct: float
    forecast_probability_up: float
    recommendation: str
    signal_price: float
    realized_price: float
    benchmark_return_pct: float
    regime: str
    portfolio_weight_pct: float
    estimated_slippage_pct: float


@dataclass(frozen=True)
class MetalsOutcomeRow:
    forecast_id: str
    asset_id: str
    vehicle_ticker: str
    horizon_days: int
    forecast_return_pct: float
    realized_return_pct: float
    absolute_error_pct: float
    squared_error: float
    directional_hit: bool
    calibration_error: float
    recommendation_hit: bool
    post_signal_return_pct: float
    excess_return_pct: float
    regime: str
    estimated_slippage_pct: float
    net_return_after_slippage_pct: float
    portfolio_contribution_pct: float
    validation_status: str


def _direction(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _recommendation_hit(recommendation: str, realized_return_pct: float) -> bool:
    action = recommendation.strip().upper()
    if action in {"BUY", "ACCUMULATE", "OVERWEIGHT"}:
        return realized_return_pct > 0
    if action in {"SELL", "REDUCE", "UNDERWEIGHT"}:
        return realized_return_pct < 0
    if action in {"HOLD", "NEUTRAL"}:
        return abs(realized_return_pct) < 2.0
    raise ValueError(f"unsupported recommendation: {recommendation}")


def evaluate_metals_outcomes(observations: Iterable[MetalsOutcomeObservation]) -> tuple[MetalsOutcomeRow, ...]:
    rows: list[MetalsOutcomeRow] = []
    seen: set[str] = set()
    for item in observations:
        if item.forecast_id in seen:
            raise ValueError(f"duplicate forecast_id: {item.forecast_id}")
        seen.add(item.forecast_id)
        if item.horizon_days <= 0 or item.signal_price <= 0 or item.realized_price <= 0:
            raise ValueError("horizon and prices must be positive")
        if not 0 <= item.forecast_probability_up <= 1:
            raise ValueError("forecast_probability_up must be between zero and one")
        realized = (item.realized_price / item.signal_price - 1.0) * 100.0
        error = item.forecast_return_pct - realized
        actual_up = 1.0 if realized > 0 else 0.0
        net = realized - item.estimated_slippage_pct
        rows.append(MetalsOutcomeRow(
            forecast_id=item.forecast_id,
            asset_id=item.asset_id,
            vehicle_ticker=item.vehicle_ticker,
            horizon_days=item.horizon_days,
            forecast_return_pct=round(item.forecast_return_pct, 6),
            realized_return_pct=round(realized, 6),
            absolute_error_pct=round(abs(error), 6),
            squared_error=round(error * error, 6),
            directional_hit=_direction(item.forecast_return_pct) == _direction(realized),
            calibration_error=round(abs(item.forecast_probability_up - actual_up), 6),
            recommendation_hit=_recommendation_hit(item.recommendation, realized),
            post_signal_return_pct=round(realized, 6),
            excess_return_pct=round(realized - item.benchmark_return_pct, 6),
            regime=item.regime,
            estimated_slippage_pct=round(item.estimated_slippage_pct, 6),
            net_return_after_slippage_pct=round(net, 6),
            portfolio_contribution_pct=round(net * item.portfolio_weight_pct / 100.0, 6),
            validation_status="PASS",
        ))
    return tuple(sorted(rows, key=lambda row: (row.horizon_days, row.asset_id, row.forecast_id)))


def summarize_metals_outcomes(rows: Iterable[MetalsOutcomeRow]) -> dict[str, object]:
    materialized = tuple(rows)
    if not materialized:
        return {"status": "NO_OUTCOMES", "outcome_count": 0}
    return {
        "status": "PASS",
        "outcome_count": len(materialized),
        "mean_absolute_error_pct": round(mean(row.absolute_error_pct for row in materialized), 6),
        "root_mean_squared_error_pct": round(mean(row.squared_error for row in materialized) ** 0.5, 6),
        "directional_accuracy_pct": round(mean(row.directional_hit for row in materialized) * 100.0, 6),
        "mean_calibration_error": round(mean(row.calibration_error for row in materialized), 6),
        "recommendation_hit_rate_pct": round(mean(row.recommendation_hit for row in materialized) * 100.0, 6),
        "mean_post_signal_return_pct": round(mean(row.post_signal_return_pct for row in materialized), 6),
        "mean_excess_return_pct": round(mean(row.excess_return_pct for row in materialized), 6),
        "mean_slippage_pct": round(mean(row.estimated_slippage_pct for row in materialized), 6),
        "total_portfolio_contribution_pct": round(sum(row.portfolio_contribution_pct for row in materialized), 6),
    }


def summarize_by_regime(rows: Iterable[MetalsOutcomeRow]) -> tuple[dict[str, object], ...]:
    groups: dict[str, list[MetalsOutcomeRow]] = {}
    for row in rows:
        groups.setdefault(row.regime, []).append(row)
    return tuple({
        "regime": regime,
        "outcome_count": len(items),
        "directional_accuracy_pct": round(mean(item.directional_hit for item in items) * 100.0, 6),
        "recommendation_hit_rate_pct": round(mean(item.recommendation_hit for item in items) * 100.0, 6),
        "mean_net_return_pct": round(mean(item.net_return_after_slippage_pct for item in items), 6),
    } for regime, items in sorted(groups.items()))


def publish_metals_outcomes(rows: Iterable[MetalsOutcomeRow], summary: Mapping[str, object], output_root: Path) -> None:
    materialized = tuple(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "metals_outcome_summary.json").write_text(json.dumps(dict(summary), indent=2, sort_keys=True), encoding="utf-8")
    (output_root / "metals_outcomes.json").write_text(json.dumps([asdict(row) for row in materialized], indent=2, sort_keys=True), encoding="utf-8")
    (output_root / "metals_regime_performance.json").write_text(json.dumps(list(summarize_by_regime(materialized)), indent=2, sort_keys=True), encoding="utf-8")
    with (output_root / "metals_outcomes.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(asdict(materialized[0]).keys()) if materialized else []
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            for row in materialized:
                writer.writerow(asdict(row))

"""UIP-native Metals forecast and decision execution.

This module consumes only UIP-owned observations and a versioned methodology registry.
It does not read or execute the standalone Metals runtime.

Model (v2):
- Benchmark momentum is the trailing 12-month change measured by observation
  dates, computed over UIP's own observations merged with the full World Bank
  monthly history when it is supplied.
- Vehicle confirmation uses only the vehicles registered to that commodity
  (vehicle_underlying), never other metals' vehicles or the cash reserve.
- Data completeness affects confidence only, never the return.
- Confidence comes from a backtest: how often the trailing 12-month direction
  matched the following 12 months for this metal.
- Horizons beyond 12 months compound the 12-month rate and are labelled as
  extrapolations with reduced confidence.
- A metal with less than a year of history gets a zero return, minimum
  confidence and HOLD.
"""
from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

MOMENTUM_MONTHS = 12
DEFAULT_BACKTEST_LOOKBACK_MONTHS = 240
DEFAULT_MINIMUM_BACKTEST_SAMPLES = 24
DEFAULT_LONG_HORIZON_CONFIDENCE_FACTOR = 0.5


@dataclass(frozen=True)
class NativeObservation:
    asset_id: str
    observation_date: str
    value: float
    source: str


@dataclass(frozen=True)
class NativeForecast:
    asset_id: str
    horizon_months: int
    as_of_date: str
    current_value: float
    projected_value: float
    expected_return: float
    annualized_return: float
    confidence: float
    recommendation: str
    model_id: str
    methodology_version: str
    component_json: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NativeCycleReport:
    status: str
    forecast_count: int
    asset_count: int
    reason_codes: tuple[str, ...]
    forecasts: tuple[NativeForecast, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "forecast_count": self.forecast_count,
            "asset_count": self.asset_count,
            "reason_codes": list(self.reason_codes),
            "forecasts": [item.to_dict() for item in self.forecasts],
        }


def load_methodology(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bounded(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _recommendation(annual_return: float, policy: Mapping[str, object]) -> str:
    if annual_return >= float(policy["strong_buy_min_return"]):
        return "STRONG_BUY"
    if annual_return >= float(policy["buy_min_return"]):
        return "BUY"
    if annual_return >= float(policy["hold_min_return"]):
        return "HOLD"
    if annual_return >= float(policy["reduce_min_return"]):
        return "REDUCE"
    return str(policy.get("otherwise", "AVOID"))


def _to_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def _months_back(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) - months
    year, month = divmod(index, 12)
    day = min(value.day, 28)
    return date(year, month + 1, day)


def _series(rows: Iterable[NativeObservation]) -> list[tuple[date, float]]:
    points: dict[date, float] = {}
    for row in rows:
        points[_to_date(row.observation_date)] = float(row.value)
    return sorted(points.items())


def _trailing_return(
    points: Sequence[tuple[date, float]],
    end_index: int | None = None,
    dates: Sequence[date] | None = None,
) -> float | None:
    """Annualized change from the last observation at least 12 months before the end.

    Returns None when there is no observation that far back.
    """
    if not points:
        return None
    end = len(points) - 1 if end_index is None else end_index
    end_date, end_value = points[end]
    target = _months_back(end_date, MOMENTUM_MONTHS)
    ordered_dates = dates if dates is not None else [point_date for point_date, _ in points]
    base_index = min(bisect_right(ordered_dates, target), end + 1) - 1
    if base_index < 0:
        return None
    base_date, base_value = points[base_index]
    if base_value <= 0 or end_value <= 0:
        return None
    elapsed_days = (end_date - base_date).days
    if elapsed_days <= 0:
        return None
    return (end_value / base_value) ** (365.25 / elapsed_days) - 1.0


def _annualized_momentum(values: Sequence[float]) -> float:
    """Legacy point-count momentum, kept for callers outside the native cycle."""
    if len(values) < 2 or values[0] <= 0 or values[-1] <= 0:
        return 0.0
    periods = max(1, len(values) - 1)
    return (values[-1] / values[0]) ** (12.0 / periods) - 1.0


def _directional_backtest(points: Sequence[tuple[date, float]], lookback_months: int) -> tuple[int, int]:
    """Count months where the trailing 12-month direction matched the next 12 months."""
    if not points:
        return 0, 0
    dates = [point_date for point_date, _ in points]
    start = _months_back(dates[-1], lookback_months)
    hits = 0
    samples = 0
    for i in range(bisect_right(dates, start) - 1 if dates[0] <= start else 0, len(points)):
        point_date, value = points[i]
        if point_date < start or value <= 0:
            continue
        forward_target = _months_back(point_date, -MOMENTUM_MONTHS)
        forward_index = bisect_right(dates, forward_target - timedelta(days=1))
        if forward_index >= len(points):
            break
        forward_date, forward_value = points[forward_index]
        if (forward_date - forward_target).days > 45:
            continue
        signal = _trailing_return(points, i, dates)
        if signal is None or signal == 0:
            continue
        realized = forward_value / value - 1.0
        if realized == 0:
            continue
        samples += 1
        if (signal > 0) == (realized > 0):
            hits += 1
    return hits, samples


def _key(asset_id: str) -> str:
    return str(asset_id).split(":")[-1].upper()


def evaluate_native_cycle(
    benchmark_observations: Iterable[NativeObservation],
    vehicle_observations: Iterable[NativeObservation],
    methodology: Mapping[str, object],
    *,
    history_observations: Iterable[NativeObservation] = (),
    vehicle_underlying: Mapping[str, str] | None = None,
) -> NativeCycleReport:
    reasons: list[str] = []
    models = methodology.get("models")
    if not isinstance(models, list) or not models:
        return NativeCycleReport("FAILED", 0, 0, ("MISSING_MODEL",), ())
    model = models[0]
    if not isinstance(model, dict):
        return NativeCycleReport("FAILED", 0, 0, ("INVALID_MODEL",), ())

    recent: dict[str, list[NativeObservation]] = {}
    for row in benchmark_observations:
        recent.setdefault(_key(row.asset_id), []).append(row)
    if not recent:
        return NativeCycleReport("INCOMPLETE", 0, 0, ("MISSING_BENCHMARK_OBSERVATIONS",), ())

    history: dict[str, list[NativeObservation]] = {}
    for row in history_observations:
        history.setdefault(_key(row.asset_id), []).append(row)

    vehicles: dict[str, list[NativeObservation]] = {}
    for row in vehicle_observations:
        vehicles.setdefault(row.asset_id.upper(), []).append(row)
    underlying = {ticker.upper(): _key(asset) for ticker, asset in (vehicle_underlying or {}).items()}

    bounds = model["forecast_bounds"]
    confidence_policy = model["confidence_policy"]
    recommendation_policy = model["recommendation_policy"]
    horizons = methodology.get("default_horizons_months", [12, 36, 60])
    minimum_confidence = float(confidence_policy["minimum"])
    maximum_confidence = float(confidence_policy["maximum"])
    lookback = int(confidence_policy.get("backtest_lookback_months", DEFAULT_BACKTEST_LOOKBACK_MONTHS))
    minimum_samples = int(confidence_policy.get("minimum_backtest_samples", DEFAULT_MINIMUM_BACKTEST_SAMPLES))
    long_factor = float(
        confidence_policy.get("long_horizon_confidence_factor", DEFAULT_LONG_HORIZON_CONFIDENCE_FACTOR)
    )
    forecasts: list[NativeForecast] = []

    for asset_id, rows in sorted(recent.items()):
        # Forecasts keep the source identity (e.g. METALS:COMMODITY:GOLD) that downstream
        # sidecars and the presentation bridge expect; the short key is only for matching.
        source_asset_id = rows[-1].asset_id.upper()
        # History first, then UIP's own observations, so UIP's value wins on the same date.
        points = _series([*history.get(asset_id, []), *rows])
        latest_date, current = points[-1]
        if current <= 0:
            reasons.append(f"NONPOSITIVE_CURRENT_VALUE:{asset_id}")
            continue

        benchmark_momentum = _trailing_return(points)
        sufficient_history = benchmark_momentum is not None

        confirming: dict[str, float] = {}
        for ticker, ticker_rows in sorted(vehicles.items()):
            if underlying.get(ticker) != asset_id:
                continue
            momentum = _trailing_return(_series(ticker_rows))
            if momentum is not None:
                confirming[ticker] = momentum
        vehicle_confirmation = mean(confirming.values()) if confirming else 0.0

        hits, samples = _directional_backtest(points, lookback)
        hit_rate = hits / samples if samples else None

        if not sufficient_history:
            annual_return = 0.0
            confidence = minimum_confidence
            recommendation = "HOLD"
            reasons.append(f"INSUFFICIENT_HISTORY:{asset_id}")
        else:
            annual_return = _bounded(
                0.45 * benchmark_momentum + 0.35 * vehicle_confirmation,
                float(bounds["minimum_annual_return"]),
                float(bounds["maximum_annual_return"]),
            )
            if hit_rate is None or samples < minimum_samples:
                confidence = minimum_confidence
            else:
                # A coin flip (50%) earns the minimum; a perfect record earns the maximum.
                skill = max(0.0, (hit_rate - 0.5) / 0.5)
                confidence = minimum_confidence + (maximum_confidence - minimum_confidence) * skill
            confidence = _bounded(confidence, minimum_confidence, maximum_confidence)
            recommendation = _recommendation(annual_return, recommendation_policy)

        base_components = {
            "model_version": "metals-native-v2",
            "benchmark_momentum": benchmark_momentum if sufficient_history else 0.0,
            "momentum_basis": "TRAILING_12M_BY_DATE" if sufficient_history else "INSUFFICIENT_HISTORY",
            "vehicle_confirmation": vehicle_confirmation,
            "confirming_vehicles": sorted(confirming),
            "vehicle_series_count": len(confirming),
            # Reported for the component decomposition; it no longer moves the return.
            "data_completeness": min(1.0, len(points) / 12.0),
            "benchmark_observation_count": len(points),
            "history_start_date": points[0][0].isoformat(),
            "backtest_hits": hits,
            "backtest_samples": samples,
            "backtest_hit_rate": hit_rate,
        }
        for horizon in horizons:
            horizon_months = int(horizon)
            projected = current * math.pow(1.0 + annual_return, horizon_months / 12.0)
            expected_return = projected / current - 1.0
            horizon_confidence = confidence
            components = dict(base_components)
            if horizon_months > MOMENTUM_MONTHS:
                components["horizon_basis"] = "EXTRAPOLATED_FROM_12M"
                horizon_confidence = _bounded(confidence * long_factor, minimum_confidence, maximum_confidence)
            else:
                components["horizon_basis"] = "MODEL_12M"
            forecasts.append(
                NativeForecast(
                    asset_id=source_asset_id,
                    horizon_months=horizon_months,
                    as_of_date=latest_date.isoformat(),
                    current_value=round(current, 8),
                    projected_value=round(projected, 8),
                    expected_return=round(expected_return, 8),
                    annualized_return=round(annual_return, 8),
                    confidence=round(horizon_confidence, 8),
                    recommendation=recommendation,
                    model_id=str(model["model_id"]),
                    methodology_version=str(methodology.get("registry_version", "unknown")),
                    component_json=json.dumps(components, sort_keys=True),
                )
            )

    if not forecasts:
        reasons.append("NO_FORECASTS_GENERATED")
        status = "INCOMPLETE"
    else:
        status = "PASS"
        reasons.append("UIP_NATIVE_FORECASTS_GENERATED")
    return NativeCycleReport(
        status=status,
        forecast_count=len(forecasts),
        asset_count=len({item.asset_id for item in forecasts}),
        reason_codes=tuple(dict.fromkeys(reasons)),
        forecasts=tuple(forecasts),
    )


def publish_native_cycle(report: NativeCycleReport, output_root: Path) -> tuple[Path, Path]:
    import csv

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest.json"
    csv_path = output_root / "latest_forecasts.csv"
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    fields = list(NativeForecast.__dataclass_fields__)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for forecast in report.forecasts:
            writer.writerow(forecast.to_dict())
    return json_path, csv_path

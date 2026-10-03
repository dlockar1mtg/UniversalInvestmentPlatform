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
- The recommendation uses the confidence-adjusted return (return x confidence);
  the reported return stays the raw model value.
- Horizons beyond 12 months compound the 12-month rate and are labelled as
  extrapolations with reduced confidence.
- A metal with less than a year of history gets a zero return, minimum
  confidence and HOLD.
- Each forecast carries a bear/bull range (historical 10th-90th percentile of
  returns over that horizon, re-centred on the forecast) and the probability of
  a positive return; each metal carries a risk profile from its monthly history.
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


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated quantile of an already sorted list."""
    position = (len(sorted_values) - 1) * q
    lower = int(math.floor(position))
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _risk_profile(
    points: Sequence[tuple[date, float]], lookback_months: int, minimum_samples: int
) -> dict[str, object] | None:
    """Risk of the benchmark itself from its monthly history over the lookback."""
    start = _months_back(points[-1][0], lookback_months)
    returns: list[float] = []
    for (previous_date, previous), (current_date, value) in zip(points, points[1:]):
        if current_date < start or previous <= 0 or value <= 0:
            continue
        if (current_date - previous_date).days > 45:
            continue
        returns.append(value / previous - 1.0)
    if len(returns) < max(minimum_samples, 2):
        return None
    average = math.fsum(returns) / len(returns)
    volatility = math.sqrt(math.fsum((r - average) ** 2 for r in returns) / (len(returns) - 1)) * math.sqrt(12)
    downside = math.sqrt(math.fsum(min(r, 0.0) ** 2 for r in returns) / len(returns)) * math.sqrt(12)
    window = [value for point_date, value in points if point_date >= start and value > 0]
    peak = window[0]
    drawdown = 0.0
    for value in window:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    ordered = sorted(returns)
    var_95 = _quantile(ordered, 0.05)
    tail = [r for r in returns if r <= var_95]
    if volatility < 0.15:
        level = "low"
    elif volatility < 0.30:
        level = "medium"
    elif volatility < 0.50:
        level = "high"
    else:
        level = "extreme"
    return {
        "annualized_volatility": round(volatility, 8),
        "downside_deviation": round(downside, 8),
        "maximum_drawdown": round(drawdown, 8),
        "value_at_risk_95": round(var_95, 8),
        "expected_shortfall_95": round(math.fsum(tail) / len(tail), 8),
        "risk_level": level,
        "risk_score": round(min(100.0, volatility / 0.60 * 100.0), 2),
        "lookback_months": lookback_months,
        "return_observations": len(returns),
        "basis": "MONTHLY_BENCHMARK_HISTORY",
    }


def _horizon_band(
    points: Sequence[tuple[date, float]], horizon_months: int, lookback_months: int, minimum_samples: int
) -> list[float] | None:
    """Sorted historical returns over the horizon, from overlapping monthly start points."""
    dates = [point_date for point_date, _ in points]
    start = _months_back(dates[-1], lookback_months)
    returns: list[float] = []
    for i, (point_date, value) in enumerate(points):
        if point_date < start or value <= 0:
            continue
        target = _months_back(point_date, -horizon_months)
        j = bisect_right(dates, target - timedelta(days=1))
        if j >= len(points):
            break
        end_date, end_value = points[j]
        if (end_date - target).days > 45 or end_value <= 0:
            continue
        returns.append(end_value / value - 1.0)
    if len(returns) < minimum_samples:
        return None
    return sorted(returns)


VALUATION_WINDOW_MONTHS = 120
TREND_WINDOW_MONTHS = 12
HISTORICAL_RANGE_MONTHS = 240


def _month_index(day: date) -> int:
    return day.year * 12 + day.month - 1


def _monthly_closes(points: Sequence[tuple[date, float]]) -> dict[int, float]:
    """Last positive observation in each calendar month (daily data collapses to one value)."""
    closes: dict[int, float] = {}
    for day, value in points:
        if value > 0:
            closes[_month_index(day)] = value
    return closes


def _window(closes: Mapping[int, float], end: int, months: int, minimum_share: float) -> list[float] | None:
    values = [closes[m] for m in range(end - months + 1, end + 1) if m in closes]
    return values if len(values) >= math.ceil(months * minimum_share) else None


def _descriptive_indicators(
    points: Sequence[tuple[date, float]], minimum_samples: int
) -> dict[str, object]:
    """Descriptive context shown instead of calls: valuation, trend and the historical 12-month range.

    Definitions match the out-of-sample signal research (scripts/research_metals_signals.py):
    valuation = latest price vs the geometric average of the last 10 years of month-end prices;
    trend = latest price vs the average of the last 12 month-end prices. Neither is a forecast.
    Each needs genuinely monthly history; annual-only series report None.
    """
    closes = _monthly_closes(points)
    latest_value = points[-1][1] if points else 0.0
    if not closes or latest_value <= 0:
        return {"valuation": None, "trend": None, "historical_12m_returns": None}
    end = max(closes)
    descriptive: dict[str, object] = {"valuation": None, "trend": None, "historical_12m_returns": None}
    decade = _window(closes, end, VALUATION_WINDOW_MONTHS, 0.9)
    if decade:
        log_average = sum(math.log(v) for v in decade) / len(decade)
        gap = math.exp(math.log(latest_value) - log_average) - 1.0
        descriptive["valuation"] = {
            "basis": "PRICE_VS_10Y_GEOMETRIC_AVERAGE",
            "window_months": VALUATION_WINDOW_MONTHS,
            "months_used": len(decade),
            "gap": gap,
            "state": "BELOW_LONG_RUN_AVERAGE" if gap < 0 else "ABOVE_LONG_RUN_AVERAGE",
        }
    year = _window(closes, end, TREND_WINDOW_MONTHS, 11 / 12)
    if year:
        gap = latest_value / (sum(year) / len(year)) - 1.0
        descriptive["trend"] = {
            "basis": "PRICE_VS_12M_AVERAGE",
            "window_months": TREND_WINDOW_MONTHS,
            "gap": gap,
            "state": "ABOVE_TREND" if gap > 0 else "BELOW_TREND",
        }
    returns = sorted(
        closes[m] / closes[m - 12] - 1.0
        for m in range(end - HISTORICAL_RANGE_MONTHS + 1, end + 1)
        if m in closes and (m - 12) in closes
    )
    if len(returns) >= minimum_samples:
        descriptive["historical_12m_returns"] = {
            "basis": "TRAILING_12M_RETURNS_NOT_A_FORECAST",
            "window_months": HISTORICAL_RANGE_MONTHS,
            "samples": len(returns),
            "p10": _quantile(returns, 0.10),
            "p50": _quantile(returns, 0.50),
            "p90": _quantile(returns, 0.90),
        }
    return descriptive


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
            confidence_adjusted_return = 0.0
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
            # The call uses the return shrunk toward zero by confidence, so a large move
            # with coin-flip skill does not become a STRONG_BUY.
            confidence_adjusted_return = annual_return * confidence
            recommendation = _recommendation(confidence_adjusted_return, recommendation_policy)

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
            "confidence_adjusted_return": confidence_adjusted_return,
            "recommendation_basis": "CONFIDENCE_ADJUSTED_12M",
            "risk": _risk_profile(points, lookback, minimum_samples) if sufficient_history else None,
            # Valuation, trend and the historical 12-month range: shown instead of calls (#217, #219).
            "descriptive": _descriptive_indicators(points, minimum_samples),
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
            band = _horizon_band(points, horizon_months, lookback, minimum_samples) if sufficient_history else None
            if band is None:
                components["bear_value"] = None
                components["bull_value"] = None
                components["probability_positive_return"] = None
            else:
                # The historical spread of this metal's returns over the horizon,
                # re-centred on the model's expected return (10th to 90th percentile).
                q10, q50, q90 = _quantile(band, 0.10), _quantile(band, 0.50), _quantile(band, 0.90)
                components["bear_value"] = round(max(0.0, current * (1.0 + expected_return + q10 - q50)), 8)
                components["bull_value"] = round(current * (1.0 + expected_return + q90 - q50), 8)
                components["probability_positive_return"] = round(
                    sum(1 for r in band if r - q50 + expected_return > 0) / len(band), 8
                )
                components["range_basis"] = "HISTORICAL_HORIZON_RETURNS_P10_P90"
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

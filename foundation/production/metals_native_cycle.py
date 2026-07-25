"""UIP-native Metals forecast and decision execution.

This module consumes only UIP-owned observations and a versioned methodology registry.
It does not read or execute the standalone Metals runtime.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence


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


def _annualized_momentum(values: Sequence[float]) -> float:
    if len(values) < 2 or values[0] <= 0 or values[-1] <= 0:
        return 0.0
    periods = max(1, len(values) - 1)
    return (values[-1] / values[0]) ** (12.0 / periods) - 1.0


def evaluate_native_cycle(
    benchmark_observations: Iterable[NativeObservation],
    vehicle_observations: Iterable[NativeObservation],
    methodology: Mapping[str, object],
) -> NativeCycleReport:
    reasons: list[str] = []
    models = methodology.get("models")
    if not isinstance(models, list) or not models:
        return NativeCycleReport("FAILED", 0, 0, ("MISSING_MODEL",), ())
    model = models[0]
    if not isinstance(model, dict):
        return NativeCycleReport("FAILED", 0, 0, ("INVALID_MODEL",), ())

    grouped: dict[str, list[NativeObservation]] = {}
    for row in benchmark_observations:
        grouped.setdefault(row.asset_id.upper(), []).append(row)
    vehicles: dict[str, list[NativeObservation]] = {}
    for row in vehicle_observations:
        vehicles.setdefault(row.asset_id.upper(), []).append(row)

    if not grouped:
        return NativeCycleReport("INCOMPLETE", 0, 0, ("MISSING_BENCHMARK_OBSERVATIONS",), ())

    bounds = model["forecast_bounds"]
    confidence_policy = model["confidence_policy"]
    recommendation_policy = model["recommendation_policy"]
    horizons = methodology.get("default_horizons_months", [12, 36, 60])
    forecasts: list[NativeForecast] = []

    for asset_id, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda item: item.observation_date)
        values = [float(item.value) for item in rows]
        current = values[-1]
        if current <= 0:
            reasons.append(f"NONPOSITIVE_CURRENT_VALUE:{asset_id}")
            continue
        benchmark_momentum = _annualized_momentum(values)

        related_vehicle_values: list[float] = []
        for ticker_rows in vehicles.values():
            ordered = sorted(ticker_rows, key=lambda item: item.observation_date)
            if ordered and ordered[-1].value > 0:
                related_vehicle_values.append(_annualized_momentum([item.value for item in ordered]))
        vehicle_confirmation = mean(related_vehicle_values) if related_vehicle_values else 0.0
        completeness = min(1.0, len(values) / 12.0)

        annual_return = (
            0.45 * benchmark_momentum
            + 0.35 * vehicle_confirmation
            + 0.20 * (completeness - 0.5) * 0.10
        )
        annual_return = _bounded(
            annual_return,
            float(bounds["minimum_annual_return"]),
            float(bounds["maximum_annual_return"]),
        )
        confidence = float(confidence_policy["base"])
        confidence += min(12, len(values)) * float(confidence_policy["history_bonus_per_observation"])
        if related_vehicle_values:
            confidence += float(confidence_policy["vehicle_confirmation_bonus"])
        confidence = _bounded(
            confidence,
            float(confidence_policy["minimum"]),
            float(confidence_policy["maximum"]),
        )

        components = {
            "benchmark_momentum": benchmark_momentum,
            "vehicle_confirmation": vehicle_confirmation,
            "data_completeness": completeness,
            "benchmark_observation_count": len(values),
            "vehicle_series_count": len(related_vehicle_values),
        }
        for horizon in horizons:
            horizon_months = int(horizon)
            projected = current * math.pow(1.0 + annual_return, horizon_months / 12.0)
            expected_return = projected / current - 1.0
            forecasts.append(
                NativeForecast(
                    asset_id=asset_id,
                    horizon_months=horizon_months,
                    as_of_date=rows[-1].observation_date,
                    current_value=round(current, 8),
                    projected_value=round(projected, 8),
                    expected_return=round(expected_return, 8),
                    annualized_return=round(annual_return, 8),
                    confidence=round(confidence, 8),
                    recommendation=_recommendation(annual_return, recommendation_policy),
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

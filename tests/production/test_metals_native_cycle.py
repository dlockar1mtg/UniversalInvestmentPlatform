from __future__ import annotations

import json
from pathlib import Path

from foundation.production.metals_native_cycle import (
    NativeObservation,
    evaluate_native_cycle,
    load_methodology,
    publish_native_cycle,
)


def _methodology():
    return {
        "registry_version": "1.0.0",
        "default_horizons_months": [12, 36, 60],
        "models": [
            {
                "model_id": "test-model",
                "forecast_bounds": {
                    "minimum_annual_return": -0.35,
                    "maximum_annual_return": 0.50,
                },
                "confidence_policy": {
                    "minimum": 0.25,
                    "maximum": 0.90,
                    "base": 0.45,
                    "history_bonus_per_observation": 0.03,
                    "vehicle_confirmation_bonus": 0.10,
                },
                "recommendation_policy": {
                    "strong_buy_min_return": 0.12,
                    "buy_min_return": 0.05,
                    "hold_min_return": -0.05,
                    "reduce_min_return": -0.12,
                    "otherwise": "AVOID",
                },
            }
        ],
    }


def _benchmarks():
    return [
        NativeObservation("GOLD", "2026-01-01", 2000.0, "test"),
        NativeObservation("GOLD", "2026-02-01", 2100.0, "test"),
        NativeObservation("SILVER", "2026-01-01", 25.0, "test"),
        NativeObservation("SILVER", "2026-02-01", 24.0, "test"),
    ]


def _vehicles():
    return [
        NativeObservation("GLD", "2026-01-01", 190.0, "test"),
        NativeObservation("GLD", "2026-02-01", 195.0, "test"),
    ]


def test_generates_three_horizons_per_asset():
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), _methodology())
    assert report.status == "PASS"
    assert report.asset_count == 2
    assert report.forecast_count == 6


def test_forecasts_include_model_evidence():
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), _methodology())
    forecast = report.forecasts[0]
    assert forecast.model_id == "test-model"
    assert forecast.methodology_version == "1.0.0"
    assert "benchmark_momentum" in json.loads(forecast.component_json)


def test_confidence_is_bounded():
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), _methodology())
    assert all(0.25 <= item.confidence <= 0.90 for item in report.forecasts)


def test_forecast_return_is_mathematically_consistent():
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), _methodology())
    for item in report.forecasts:
        expected = item.projected_value / item.current_value - 1.0
        assert abs(expected - item.expected_return) < 1e-7


def test_missing_benchmarks_is_incomplete():
    report = evaluate_native_cycle([], _vehicles(), _methodology())
    assert report.status == "INCOMPLETE"
    assert report.reason_codes == ("MISSING_BENCHMARK_OBSERVATIONS",)


def test_missing_model_fails():
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), {"models": []})
    assert report.status == "FAILED"
    assert report.reason_codes == ("MISSING_MODEL",)


def test_publication_writes_json_and_csv(tmp_path: Path):
    report = evaluate_native_cycle(_benchmarks(), _vehicles(), _methodology())
    json_path, csv_path = publish_native_cycle(report, tmp_path)
    assert json_path.exists()
    assert csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["forecast_count"] == 6


def test_repository_methodology_registry_loads():
    root = Path(__file__).resolve().parents[2]
    methodology = load_methodology(root / "config" / "metals" / "model_methodology_registry.json")
    assert methodology["runtime"] == "UniversalInvestmentPlatform"
    assert methodology["external_runtime_required"] is False

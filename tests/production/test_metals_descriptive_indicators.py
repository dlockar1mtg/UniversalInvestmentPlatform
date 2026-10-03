import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from foundation.production.metals_native_cycle import (
    NativeObservation,
    _descriptive_indicators,
    evaluate_native_cycle,
)

ROOT = Path(__file__).resolve().parents[2]


def _monthly(n, f, start=(2000, 1)):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 15), f(i)))
    return out


def test_valuation_trend_and_range_on_monthly_history():
    points = _monthly(300, lambda i: 100 * 1.01 ** i)
    d = _descriptive_indicators(points, 24)
    expected_trend = 100 * 1.01 ** 299 / (sum(100 * 1.01 ** i for i in range(288, 300)) / 12) - 1
    expected_value = math.exp(
        math.log(100 * 1.01 ** 299) - sum(math.log(100 * 1.01 ** i) for i in range(180, 300)) / 120
    ) - 1
    assert d["trend"]["gap"] == pytest.approx(expected_trend) and d["trend"]["state"] == "ABOVE_TREND"
    assert d["valuation"]["gap"] == pytest.approx(expected_value)
    assert d["valuation"]["state"] == "ABOVE_LONG_RUN_AVERAGE"
    band = d["historical_12m_returns"]
    assert band["samples"] == 240 and band["p50"] == pytest.approx(1.01 ** 12 - 1)
    assert band["basis"] == "TRAILING_12M_RETURNS_NOT_A_FORECAST"


def test_daily_observations_collapse_to_month_ends():
    points = _monthly(300, lambda i: 100 * 1.01 ** i)
    start = points[-1][0] + timedelta(days=20)
    daily = [(start + timedelta(days=k), points[-1][1] * (1 + 0.0001 * k)) for k in range(60)]
    d = _descriptive_indicators(points + daily, 24)
    assert d["valuation"]["months_used"] <= 120 and d["trend"] is not None


def test_annual_only_history_reports_nothing():
    annual = [(date(year, 1, 1), 30.0 + year % 7) for year in range(1980, 2026)]
    assert _descriptive_indicators(annual, 24) == {"valuation": None, "trend": None, "historical_12m_returns": None}


def test_falling_prices_are_below_trend_and_below_average():
    d = _descriptive_indicators(_monthly(300, lambda i: 100 * 0.995 ** i), 24)
    assert d["trend"]["state"] == "BELOW_TREND" and d["valuation"]["state"] == "BELOW_LONG_RUN_AVERAGE"


def test_the_twelve_month_forecast_publishes_the_descriptive_block():
    methodology = json.loads((ROOT / "config" / "metals" / "model_methodology_registry.json").read_text(encoding="utf-8-sig"))
    rows = [
        NativeObservation("METALS:COMMODITY:GOLD", day.isoformat(), value, "test")
        for day, value in _monthly(300, lambda i: 100 * 1.005 ** i)
    ]
    report = evaluate_native_cycle(rows, [], methodology)
    forecast = next(f for f in report.forecasts if f.asset_id.upper().endswith("GOLD") and int(f.horizon_months) == 12)
    descriptive = json.loads(forecast.component_json)["descriptive"]
    assert descriptive["valuation"]["state"] in {"ABOVE_LONG_RUN_AVERAGE", "BELOW_LONG_RUN_AVERAGE"}
    assert descriptive["trend"]["state"] == "ABOVE_TREND"
    assert descriptive["historical_12m_returns"]["samples"] >= 24

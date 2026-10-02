import json

from foundation.production.metals_native_cycle import NativeObservation, evaluate_native_cycle


def _methodology():
    return {
        "registry_version": "2.0.0",
        "default_horizons_months": [12, 36, 60],
        "models": [
            {
                "model_id": "test-model",
                "forecast_bounds": {"minimum_annual_return": -0.35, "maximum_annual_return": 0.50},
                "confidence_policy": {
                    "minimum": 0.25,
                    "maximum": 0.90,
                    "base": 0.45,
                    "history_bonus_per_observation": 0.03,
                    "vehicle_confirmation_bonus": 0.10,
                },
                "recommendation_policy": {
                    "strong_buy_min_return": 0.12,
                    "buy_min_return": 0.06,
                    "hold_min_return": -0.02,
                    "reduce_min_return": -0.08,
                },
            }
        ],
    }


def _monthly(asset, start_year, months, start_value, monthly_growth):
    rows = []
    value = start_value
    for i in range(months):
        year, month = divmod(start_year * 12 + i, 12)
        rows.append(NativeObservation(asset, f"{year:04d}-{month + 1:02d}-01", round(value, 6), "history"))
        value *= 1 + monthly_growth
    return rows


def _components(report, asset, horizon=12):
    forecast = next(f for f in report.forecasts if f.asset_id == asset and f.horizon_months == horizon)
    return forecast, json.loads(forecast.component_json)


def _daily(ticker, start_value, daily_growth, days=400):
    from datetime import date, timedelta

    start = date(2025, 8, 1)
    return [
        NativeObservation(ticker, (start + timedelta(days=i)).isoformat(), start_value * (1 + daily_growth) ** i, "q")
        for i in range(days)
    ]


def test_momentum_uses_dates_and_full_history_not_point_count():
    # Three recent points two months apart used to be annualized as (last/first)^6.
    recent = [
        NativeObservation("URANIUM", "2026-06-01", 70.0, "eia"),
        NativeObservation("URANIUM", "2026-07-01", 75.0, "eia"),
        NativeObservation("URANIUM", "2026-08-01", 80.0, "eia"),
    ]
    history = _monthly("uranium", 2024, 26, 70.0, 0.005)  # Jan 2024 .. Feb 2026, about +6%/yr
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=history)
    forecast, components = _components(report, "URANIUM")
    assert components["momentum_basis"] == "TRAILING_12M_BY_DATE"
    # 80 vs the Aug 2025 history value (70 * 1.005^19 = 76.9) is about +4%,
    # not the point-count annualization (80/70)^6 - 1 = +122%.
    assert 0.02 < components["benchmark_momentum"] < 0.06
    assert forecast.annualized_return < 0.50


def test_less_than_a_year_of_history_is_low_confidence_hold():
    recent = [
        NativeObservation("URANIUM", "2026-06-01", 70.0, "eia"),
        NativeObservation("URANIUM", "2026-08-01", 90.0, "eia"),
    ]
    report = evaluate_native_cycle(recent, [], _methodology())
    forecast, components = _components(report, "URANIUM")
    assert forecast.recommendation == "HOLD"
    assert forecast.annualized_return == 0.0
    assert forecast.confidence == 0.25
    assert components["momentum_basis"] == "INSUFFICIENT_HISTORY"
    assert "INSUFFICIENT_HISTORY:URANIUM" in report.reason_codes


def test_vehicles_confirm_only_their_own_metal_and_cash_never_counts():
    history = _monthly("gold", 2020, 80, 1500.0, 0.01) + _monthly("copper", 2020, 80, 6000.0, 0.01)
    recent = [NativeObservation("GOLD", "2026-09-01", 3400.0, "wb"), NativeObservation("COPPER", "2026-09-01", 13000.0, "wb")]
    vehicles = _daily("GLD", 200.0, 0.001) + _daily("COPX", 40.0, -0.002) + _daily("BIL", 91.0, 0.0001)
    underlying = {
        "GLD": "metals:commodity:gold",
        "COPX": "metals:commodity:copper",
        "BIL": "metals:reserve:usd",
    }
    report = evaluate_native_cycle(
        recent, vehicles, _methodology(), history_observations=history, vehicle_underlying=underlying
    )
    _, gold = _components(report, "GOLD")
    _, copper = _components(report, "COPPER")
    assert gold["confirming_vehicles"] == ["GLD"]
    assert copper["confirming_vehicles"] == ["COPX"]
    assert gold["vehicle_confirmation"] > 0 > copper["vehicle_confirmation"]


def test_completeness_no_longer_moves_the_return():
    history = _monthly("silver", 2015, 140, 15.0, 0.0)  # flat for 11+ years
    recent = [NativeObservation("SILVER", "2026-09-01", 15.0, "wb")]
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=history)
    forecast, components = _components(report, "SILVER")
    # A flat price is a zero forecast; completeness is reported but adds nothing.
    assert forecast.annualized_return == 0.0
    assert components["data_completeness"] == 1.0


def test_confidence_comes_from_the_backtest_and_differs_by_metal():
    import math

    steady = _monthly("gold", 2000, 320, 300.0, 0.008)  # steady trend: direction always right
    choppy = [
        NativeObservation("nickel", row.observation_date, 10000.0 * (1 + 0.5 * math.sin(i / 3.0)), "history")
        for i, row in enumerate(_monthly("nickel", 2000, 320, 1.0, 0.0))
    ]
    recent = [NativeObservation("GOLD", "2026-09-01", 4000.0, "wb"), NativeObservation("NICKEL", "2026-09-01", 10000.0, "wb")]
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=steady + choppy)
    gold, gold_c = _components(report, "GOLD")
    nickel, nickel_c = _components(report, "NICKEL")
    assert gold_c["backtest_samples"] >= 24 and gold_c["backtest_hit_rate"] > 0.95
    assert gold.confidence > 0.85
    assert nickel_c["backtest_hit_rate"] < gold_c["backtest_hit_rate"]
    assert nickel.confidence < gold.confidence


def test_long_horizons_are_labelled_extrapolations_with_lower_confidence():
    history = _monthly("gold", 2000, 320, 300.0, 0.008)
    recent = [NativeObservation("GOLD", "2026-09-01", 4000.0, "wb")]
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=history)
    twelve, twelve_c = _components(report, "GOLD", 12)
    sixty, sixty_c = _components(report, "GOLD", 60)
    assert twelve_c["horizon_basis"] == "MODEL_12M"
    assert sixty_c["horizon_basis"] == "EXTRAPOLATED_FROM_12M"
    assert sixty.confidence < twelve.confidence


def test_uip_observation_wins_over_history_on_the_same_date():
    history = _monthly("gold", 2024, 33, 2000.0, 0.01)  # ends 2026-09-01
    recent = [NativeObservation("GOLD", "2026-09-01", 9999.0, "wb")]
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=history)
    forecast, _ = _components(report, "GOLD")
    assert forecast.current_value == 9999.0
    assert forecast.as_of_date == "2026-09-01"


def test_forecasts_keep_the_source_identity_while_matching_on_the_metal():
    history = _monthly("gold", 2020, 80, 1500.0, 0.01)
    recent = [NativeObservation("metals:commodity:gold", "2026-09-01", 3400.0, "wb")]
    vehicles = _daily("GLD", 200.0, 0.001)
    report = evaluate_native_cycle(
        recent,
        vehicles,
        _methodology(),
        history_observations=history,
        vehicle_underlying={"GLD": "metals:commodity:gold"},
    )
    forecast, components = _components(report, "METALS:COMMODITY:GOLD")
    assert {f.asset_id for f in report.forecasts} == {"METALS:COMMODITY:GOLD"}
    assert components["benchmark_observation_count"] > 12
    assert components["confirming_vehicles"] == ["GLD"]


def test_recommendation_uses_the_confidence_adjusted_return():
    import math

    # Choppy history: the backtest is near a coin flip, so confidence sits near the minimum.
    choppy = [
        NativeObservation("silver", row.observation_date, 20.0 * (1 + 0.5 * math.sin(i / 3.0)), "history")
        for i, row in enumerate(_monthly("silver", 2000, 320, 1.0, 0.0))
    ]
    # A big latest print makes the raw 12-month return large.
    recent = [NativeObservation("SILVER", "2026-09-01", 40.0, "wb")]
    report = evaluate_native_cycle(recent, [], _methodology(), history_observations=choppy)
    forecast, components = _components(report, "SILVER")
    assert forecast.annualized_return >= 0.12  # raw return alone would be STRONG_BUY
    adjusted = components["confidence_adjusted_return"]
    assert abs(adjusted - forecast.annualized_return * forecast.confidence) < 1e-6
    assert components["recommendation_basis"] == "CONFIDENCE_ADJUSTED_12M"
    expected = "BUY" if adjusted >= 0.06 else ("HOLD" if adjusted >= -0.02 else "REDUCE")
    assert adjusted < 0.12 and forecast.recommendation == expected

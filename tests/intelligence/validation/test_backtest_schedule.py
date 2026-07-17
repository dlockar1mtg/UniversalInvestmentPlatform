from datetime import date

from foundation.intelligence.validation import (
    BacktestConfiguration,
    RebalanceFrequency,
    generate_prediction_dates,
)


def config(frequency: RebalanceFrequency, warmup_days: int = 0):
    return BacktestConfiguration(
        backtest_id="test",
        model_id="model",
        model_version="1.0.0",
        asset_class="crypto",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 30),
        horizons_days=(30,),
        rebalance_frequency=frequency,
        warmup_days=warmup_days,
    )


def test_daily_schedule_respects_warmup() -> None:
    dates = generate_prediction_dates(config(RebalanceFrequency.DAILY, 2))
    assert dates[0] == date(2026, 1, 3)


def test_weekly_schedule_is_deterministic() -> None:
    dates = generate_prediction_dates(config(RebalanceFrequency.WEEKLY))
    assert dates[:3] == (
        date(2026, 1, 1),
        date(2026, 1, 8),
        date(2026, 1, 15),
    )


def test_monthly_schedule_uses_month_end() -> None:
    dates = generate_prediction_dates(config(RebalanceFrequency.MONTHLY))
    assert dates == (
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    )


def test_quarterly_schedule_uses_quarter_end() -> None:
    dates = generate_prediction_dates(config(RebalanceFrequency.QUARTERLY))
    assert dates == (date(2026, 3, 31),)


def test_annual_schedule_can_be_empty() -> None:
    dates = generate_prediction_dates(config(RebalanceFrequency.ANNUALLY))
    assert dates == ()

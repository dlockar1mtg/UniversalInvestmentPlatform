from datetime import date

from scripts.build_metals_native_freshness_sidecar import build_row, classify, health_score


POLICIES = {
    "world_bank": {"frequency": "MONTHLY", "current_max_age_days": 45, "stale_after_days": 75},
    "eia": {"frequency": "ANNUAL", "current_max_age_days": 365, "stale_after_days": 730},
    "yfinance_daily_market_input": {"frequency": "DAILY", "current_max_age_days": 3, "stale_after_days": 5},
}


def test_vehicle_status_handles_weekends_without_one_day_staleness() -> None:
    policy = POLICIES["yfinance_daily_market_input"]
    assert classify(0, policy) == "CURRENT"
    assert classify(3, policy) == "CURRENT"
    assert classify(4, policy) == "AGING"
    assert classify(5, policy) == "AGING"
    assert classify(6, policy) == "STALE"


def test_health_score_is_deterministic_and_bounded() -> None:
    policy = POLICIES["world_bank"]
    assert health_score(0, policy) == 100.0
    assert health_score(75, policy) == 0.0
    assert health_score(100, policy) == 0.0


def test_native_row_uses_explicit_nonlegacy_semantics() -> None:
    row = build_row(
        series_key="WORLD_BANK::GOLD_MONTHLY",
        source="world_bank",
        observed="2026-08-01",
        as_of=date(2026, 9, 10),
        policies=POLICIES,
    )
    assert row["frequency"] == "MONTHLY"
    assert row["age_days"] == 40
    assert row["freshness_status"] == "CURRENT"
    assert row["health_score"] == "46.67"
    assert "UIP_NATIVE_METALS_DATA_FRESHNESS_V1" in row["message"]

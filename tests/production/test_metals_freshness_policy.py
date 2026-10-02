import json
from pathlib import Path

from foundation.production.hosted_refresh_status import _freshness_classification


def test_monthly_source_uses_a_monthly_limit():
    # World Bank metals data is dated the 1st and published about a month later.
    config = {"daily_schedule_utc": "23 12 * * *", "source_data_cadence": "MONTHLY"}
    assert _freshness_classification(62, config) == (
        "CURRENT",
        75,
        "MONTHLY_SOURCE_CADENCE_PLUS_PUBLICATION_LAG",
    )
    assert _freshness_classification(80, config)[0] == "STALE"


def test_daily_domains_keep_the_two_day_limit():
    assert _freshness_classification(3, {"daily_schedule_utc": "15 11 * * 1-6"}) == (
        "STALE",
        2,
        "DAILY_CADENCE_PLUS_ONE_DAY_GRACE",
    )


def test_metals_is_registered_as_a_monthly_source():
    registry = json.loads(
        Path("config/orchestration/r4_refresh_operations_registry.json").read_text(encoding="utf-8-sig")
    )
    assert registry["domains"]["metals"]["source_data_cadence"] == "MONTHLY"
    assert "source_data_cadence" not in registry["domains"]["crypto"]

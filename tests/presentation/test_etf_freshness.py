from datetime import datetime, timezone

from foundation.presentation.etf_freshness import allowed_hours, is_fresh


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_weekday_limit_stays_30_hours():
    started = utc(2026, 10, 21, 22, 30)  # Wednesday evening run
    assert is_fresh(started, utc(2026, 10, 22, 23, 0))  # 24.5 h
    assert not is_fresh(started, utc(2026, 10, 23, 6, 0))  # 31.5 h, Friday morning


def test_saturday_run_covers_monday_until_monday_nights_run():
    started = utc(2026, 10, 24, 17, 27)  # Saturday full refresh (actual Oct 24 start)
    assert allowed_hours(started, utc(2026, 10, 26, 19, 44)) == 78
    assert is_fresh(started, utc(2026, 10, 26, 19, 44))  # Monday 2:44 PM CT publication, 50 h
    assert is_fresh(started, utc(2026, 10, 27, 14, 0))  # Tuesday's 14:00 publication even if Monday's run slipped, 68.5 h
    assert not is_fresh(started, utc(2026, 10, 28, 0, 0))  # 78.5 h: Monday's run is overdue


def test_friday_run_bridges_a_failed_saturday():
    started = utc(2026, 10, 23, 23, 0)
    assert is_fresh(started, utc(2026, 10, 26, 14, 0))  # 63 h, Monday morning


def test_clock_skew_counts_as_fresh():
    assert is_fresh(utc(2026, 10, 27, 12, 0), utc(2026, 10, 27, 11, 59))

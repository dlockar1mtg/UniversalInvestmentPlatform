"""Is the newest ETF market-data run recent enough to publish?

The ETF workflow runs Monday-Friday after the US close plus a Saturday full refresh, and never on
Sunday. A flat 30-hour limit therefore dropped ETFs from every publication between Saturday's run and
Monday night's (Oct 26, 2026). Markets are shut over the weekend, so when the gap since the run
includes a Sunday, two more days are allowed.

Usage: python -m foundation.presentation.etf_freshness <run_started_at ISO-8601>  (exit 0 = fresh)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys

BASE_HOURS = 30
WEEKEND_EXTRA_HOURS = 48


def allowed_hours(started: datetime, now: datetime) -> int:
    day = started.date()
    while day <= now.date():
        if day.weekday() == 6:  # Sunday (UTC)
            return BASE_HOURS + WEEKEND_EXTRA_HOURS
        day += timedelta(days=1)
    return BASE_HOURS


def is_fresh(started: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    age_hours = (now - started).total_seconds() / 3600
    return age_hours <= allowed_hours(started, now)  # a negative age (clock skew) counts as fresh


def _parse(text: str) -> datetime:
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def main(argv: list[str]) -> int:
    started = _parse(argv[0])
    now = datetime.now(timezone.utc)
    age = (now - started).total_seconds() / 3600
    limit = allowed_hours(started, now)
    print(f"ETF run started {started.isoformat()} is {age:.1f} h old (limit {limit} h)")
    return 0 if is_fresh(started, now) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

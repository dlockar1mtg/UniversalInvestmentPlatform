from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TICKERS = ("GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM")
BASE_URL = "https://data.alpaca.markets/v2/stocks"
NY = ZoneInfo("America/New_York")
MIN_SESSIONS = 20
MAX_WEEKDAYS_TO_PROBE = 40
WINDOW_START = dt_time(15, 50)
WINDOW_END = dt_time(16, 0)


def _request_json(url: str, key_id: str, secret_key: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret_key,
            "Accept": "application/json",
            "User-Agent": "UIP-Metals-Spread-Evidence-V1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _window_utc(session_date: date) -> tuple[str, str]:
    start_local = datetime.combine(session_date, WINDOW_START, tzinfo=NY)
    end_local = datetime.combine(session_date, WINDOW_END, tzinfo=NY)
    return (
        start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def _spread_bps(row: dict, expected_date: date) -> float | None:
    try:
        bid = float(row["bp"])
        ask = float(row["ap"])
        timestamp = datetime.fromisoformat(str(row["t"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    if not (math.isfinite(bid) and math.isfinite(ask)):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    local = timestamp.astimezone(NY)
    if local.date() != expected_date or local.weekday() >= 5:
        return None
    current = local.timetz().replace(tzinfo=None)
    if not (WINDOW_START <= current <= WINDOW_END):
        return None
    midpoint = (ask + bid) / 2
    if midpoint <= 0:
        return None
    return ((ask - bid) / midpoint) * 10000


def _fetch_session_quotes(ticker: str, session_date: date, key_id: str, secret_key: str) -> tuple[list[dict], int]:
    start, end = _window_utc(session_date)
    page_token: str | None = None
    rows: list[dict] = []
    pages = 0
    seen_tokens: set[str] = set()

    while True:
        params = {
            "start": start,
            "end": end,
            "feed": "sip",
            "limit": "10000",
            "sort": "asc",
        }
        if page_token:
            params["page_token"] = page_token
        url = f"{BASE_URL}/{urllib.parse.quote(ticker)}/quotes?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, key_id, secret_key)
        pages += 1
        if "quotes" not in payload:
            raise RuntimeError(f"Unexpected Alpaca quote payload for {ticker} on {session_date}: quotes field missing")
        quotes = payload.get("quotes")
        if quotes is None:
            quotes = []
        if not isinstance(quotes, list):
            raise RuntimeError(f"Unexpected Alpaca quote payload for {ticker} on {session_date}: quotes is not list/null")
        rows.extend(quotes)
        next_token = payload.get("next_page_token")
        if not next_token:
            break
        next_token = str(next_token)
        if next_token in seen_tokens:
            raise RuntimeError(f"Repeated Alpaca page token for {ticker} on {session_date}")
        seen_tokens.add(next_token)
        page_token = next_token

    return rows, pages


def _candidate_dates(today: date) -> list[date]:
    result: list[date] = []
    cursor = today - timedelta(days=1)
    while len(result) < MAX_WEEKDAYS_TO_PROBE:
        if cursor.weekday() < 5:
            result.append(cursor)
        cursor -= timedelta(days=1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/operations/metals/alpaca_spread_evidence_v1/evidence.json")
    parser.add_argument("--request-delay-seconds", type=float, default=0.35)
    args = parser.parse_args()

    key_id = os.environ.get("ALPACA_API_KEY_ID", "").strip()
    secret_key = os.environ.get("ALPACA_API_SECRET_KEY", "").strip()
    if not key_id or not secret_key:
        raise RuntimeError("Alpaca credentials are required through repository secrets")

    as_of_utc = datetime.now(timezone.utc)
    candidates = _candidate_dates(as_of_utc.astimezone(NY).date())
    per_ticker: dict[str, dict] = {}

    for ticker in TICKERS:
        session_rows: list[dict] = []
        total_pages = 0
        probed_weekdays = 0

        for session_date in candidates:
            rows, pages = _fetch_session_quotes(ticker, session_date, key_id, secret_key)
            total_pages += pages
            probed_weekdays += 1
            spreads = [value for row in rows if (value := _spread_bps(row, session_date)) is not None]
            if spreads:
                session_rows.append({
                    "observation_date": session_date.isoformat(),
                    "valid_quote_count": len(spreads),
                    "session_median_relative_spread_bps": statistics.median(spreads),
                })
            if len(session_rows) >= MIN_SESSIONS:
                break
            time.sleep(max(0.0, args.request_delay_seconds))

        if len(session_rows) < MIN_SESSIONS:
            raise RuntimeError(f"Spread rehearsal failed for {ticker}: only {len(session_rows)} valid sessions")

        latest_twenty = sorted(session_rows, key=lambda row: row["observation_date"])[-MIN_SESSIONS:]
        final_spread = statistics.median(row["session_median_relative_spread_bps"] for row in latest_twenty)
        per_ticker[ticker] = {
            "feed": "sip",
            "source_authority": "Alpaca Market Data",
            "session_window_local": "15:50:00-16:00:00 America/New_York",
            "distinct_session_count": len(latest_twenty),
            "first_session": latest_twenty[0]["observation_date"],
            "last_session": latest_twenty[-1]["observation_date"],
            "median_relative_bid_ask_spread_bps": final_spread,
            "session_medians": latest_twenty,
            "fully_consumed_page_count": total_pages,
            "probed_weekday_count": probed_weekdays,
            "pagination_complete": True,
        }

    evidence = {
        "status": "METALS_ALPACA_SPREAD_EVIDENCE_V1_REHEARSAL_PASS",
        "authority_id": "UIP_NATIVE_METALS_VEHICLE_LIQUIDITY_V1",
        "methodology_version": "1.1.0",
        "provider": "alpaca_market_data",
        "feed": "sip",
        "required_ticker_count": len(TICKERS),
        "resolved_ticker_count": len(per_ticker),
        "minimum_distinct_sessions_required": MIN_SESSIONS,
        "session_aggregation": "median relative spread within each session",
        "cross_session_aggregation": "median of the latest 20 session medians",
        "as_of_utc": as_of_utc.isoformat(),
        "per_ticker": per_ticker,
        "spread_evidence_complete_for_exact_10_tickers": set(per_ticker) == set(TICKERS),
        "production_quote_collection_authorized": False,
        "preferred_vehicle_ranking_ready": False,
        "publication_write_performed": False,
        "automatic_execution_authorized": False,
        "credentials_persisted": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

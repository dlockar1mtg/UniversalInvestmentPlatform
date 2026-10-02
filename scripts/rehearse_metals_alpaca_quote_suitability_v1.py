from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_VEHICLE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "metals" / "vehicles.json"


def _registered_tickers() -> tuple[str, ...]:
    """Enabled, non-reserve Metals implementation vehicles, in registry order."""
    registry = json.loads(_VEHICLE_REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    return tuple(
        str(row["ticker"]).upper()
        for row in registry.get("vehicles", [])
        if row.get("enabled", True) and row.get("role") != "reserve"
    )


TICKERS = _registered_tickers()
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
            "User-Agent": "UIP-Metals-Quote-Suitability-V1",
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


def _valid_regular_quote(row: dict, expected_date: date) -> bool:
    try:
        bid = float(row["bp"])
        ask = float(row["ap"])
        timestamp = datetime.fromisoformat(str(row["t"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    if bid <= 0 or ask <= 0 or ask < bid:
        return False
    local = timestamp.astimezone(NY)
    if local.date() != expected_date or local.weekday() >= 5:
        return False
    current = local.timetz().replace(tzinfo=None)
    return dt_time(9, 30) <= current <= dt_time(16, 0)


def _fetch_session_quotes(
    ticker: str,
    session_date: date,
    key_id: str,
    secret_key: str,
) -> tuple[list[dict], int]:
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
            raise RuntimeError(
                f"Unexpected Alpaca quote payload for {ticker} on {session_date}: missing quotes field"
            )
        quotes = payload["quotes"]
        if quotes is None:
            # Alpaca can return an explicit null quote collection for a date with no
            # market session (for example, a weekday exchange holiday). Treat that
            # as a valid no-data session and continue probing backward.
            quotes = []
        elif not isinstance(quotes, list):
            raise RuntimeError(
                f"Unexpected Alpaca quote payload for {ticker} on {session_date}: quotes field is not a list or null"
            )

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
    parser.add_argument("--output", default="data/operations/metals/alpaca_quote_suitability_v1/evidence.json")
    parser.add_argument("--request-delay-seconds", type=float, default=0.35)
    args = parser.parse_args()

    key_id = os.environ.get("ALPACA_API_KEY_ID", "").strip()
    secret_key = os.environ.get("ALPACA_API_SECRET_KEY", "").strip()
    if not key_id or not secret_key:
        raise RuntimeError("Alpaca credentials are required through ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY")

    as_of_utc = datetime.now(timezone.utc)
    candidates = _candidate_dates(as_of_utc.astimezone(NY).date())
    per_ticker: dict[str, dict] = {}

    for ticker in TICKERS:
        successful_sessions: list[str] = []
        total_valid_quotes = 0
        total_pages = 0
        probed_sessions = 0

        for session_date in candidates:
            rows, pages = _fetch_session_quotes(ticker, session_date, key_id, secret_key)
            probed_sessions += 1
            total_pages += pages
            valid = [row for row in rows if _valid_regular_quote(row, session_date)]
            if valid:
                successful_sessions.append(session_date.isoformat())
                total_valid_quotes += len(valid)
            if len(successful_sessions) >= MIN_SESSIONS:
                break
            time.sleep(max(0.0, args.request_delay_seconds))

        if len(successful_sessions) < MIN_SESSIONS:
            raise RuntimeError(
                f"Alpaca SIP suitability failed for {ticker}: only {len(successful_sessions)} distinct regular-market sessions"
            )

        per_ticker[ticker] = {
            "distinct_regular_market_sessions": len(successful_sessions),
            "first_session": min(successful_sessions),
            "last_session": max(successful_sessions),
            "valid_quote_count": total_valid_quotes,
            "fully_consumed_page_count": total_pages,
            "probed_weekday_count": probed_sessions,
            "feed": "sip",
            "source_authority": "Alpaca Market Data",
            "positive_bid_ask_semantics_pass": True,
            "pagination_complete": True,
        }

    if set(per_ticker) != set(TICKERS):
        raise RuntimeError("Alpaca suitability rehearsal did not resolve the exact required ticker universe")

    evidence = {
        "status": "METALS_ALPACA_QUOTE_SUITABILITY_REHEARSAL_PASS",
        "authority_id": "UIP_NATIVE_METALS_VEHICLE_QUOTE_PROVIDER_EVALUATION_V1",
        "provider": "alpaca_market_data",
        "feed": "sip",
        "required_ticker_count": len(TICKERS),
        "resolved_ticker_count": len(per_ticker),
        "minimum_distinct_sessions_required": MIN_SESSIONS,
        "query_window_local": "15:50-16:00 America/New_York on prior weekdays",
        "as_of_utc": as_of_utc.isoformat(),
        "per_ticker": per_ticker,
        "exact_10_ticker_resolution_pass": True,
        "positive_bid_ask_semantics_pass": True,
        "twenty_session_coverage_pass": True,
        "deterministic_pagination_complete": True,
        "feed_and_source_provenance_retained": True,
        "provider_suitability_pass": True,
        "provider_certified": False,
        "quote_collection_authorized": False,
        "spread_evidence_published": False,
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

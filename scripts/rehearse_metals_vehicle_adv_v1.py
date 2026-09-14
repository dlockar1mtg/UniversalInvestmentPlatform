from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import fmean

EXPECTED_TICKERS = (
    "GLD",
    "IAU",
    "SGOL",
    "SLV",
    "SIVR",
    "PPLT",
    "CPER",
    "COPX",
    "URA",
    "URNM",
)
SOURCE_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
WINDOW_SESSIONS = 30


def _find_price_history(root: Path) -> Path:
    matches = [
        path
        for path in root.rglob("metals_price_history.csv")
        if path.as_posix().endswith(
            "operations/metals/native_rich_history/metals_price_history.csv"
        )
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one certified Metals price-history CSV under artifact root; "
            f"found {len(matches)}"
        )
    return matches[0]


def _parse_timestamp(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("Same-date revision selection requires collected_at_utc")
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _select_latest_revision(rows: list[dict[str, str]]) -> dict[str, str]:
    ranked = sorted(
        rows,
        key=lambda row: (
            _parse_timestamp(row.get("collected_at_utc", "")),
            str(row.get("source_run_id", "")),
        ),
    )
    selected = ranked[-1]
    selected_stamp = _parse_timestamp(selected.get("collected_at_utc", ""))
    tied = [
        row
        for row in ranked
        if _parse_timestamp(row.get("collected_at_utc", "")) == selected_stamp
        and str(row.get("source_run_id", "")) == str(selected.get("source_run_id", ""))
    ]
    if len(tied) > 1:
        economic_values = {
            (str(row.get("close_usd", "")), str(row.get("volume", ""))) for row in tied
        }
        if len(economic_values) != 1:
            raise RuntimeError(
                "Ambiguous same-date source revision has identical provenance but differing economic values"
            )
    return selected


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise RuntimeError("Certified Metals price-history CSV is empty")
    return rows


def _calculate_adv(rows: list[dict[str, str]], ticker: str) -> dict[str, object]:
    vehicle_rows = [row for row in rows if str(row.get("ticker", "")).upper() == ticker]
    if not vehicle_rows:
        raise RuntimeError(f"No certified price-history rows found for {ticker}")

    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in vehicle_rows:
        if str(row.get("source_authority", "")) != SOURCE_AUTHORITY:
            raise RuntimeError(
                f"Unexpected source authority for {ticker}: {row.get('source_authority')}"
            )
        expected_asset_id = f"metals:vehicle:{ticker}"
        if str(row.get("asset_id", "")) != expected_asset_id:
            raise RuntimeError(
                f"Unexpected vehicle identity for {ticker}: {row.get('asset_id')}"
            )
        observation_date = str(row.get("observation_date", "")).strip()
        if not observation_date:
            raise RuntimeError(f"Blank observation date for {ticker}")
        by_date[observation_date].append(row)

    selected = [
        _select_latest_revision(revisions)
        for _, revisions in sorted(by_date.items(), key=lambda item: item[0])
    ]
    if len(selected) < WINDOW_SESSIONS:
        raise RuntimeError(
            f"{ticker} has only {len(selected)} distinct sessions; {WINDOW_SESSIONS} required"
        )
    window = selected[-WINDOW_SESSIONS:]

    dollar_volumes: list[float] = []
    for row in window:
        try:
            close = float(str(row.get("close_usd", "")))
            volume = float(str(row.get("volume", "")))
        except ValueError as exc:
            raise RuntimeError(f"Invalid close/volume for {ticker}") from exc
        if close <= 0 or volume < 0:
            raise RuntimeError(f"Non-positive close or negative volume for {ticker}")
        dollar_volumes.append(close * volume)

    duplicate_session_count = sum(1 for revisions in by_date.values() if len(revisions) > 1)
    return {
        "ticker": ticker,
        "asset_id": f"metals:vehicle:{ticker}",
        "source_authority": SOURCE_AUTHORITY,
        "window_sessions": WINDOW_SESSIONS,
        "window_start_date": str(window[0]["observation_date"]),
        "window_end_date": str(window[-1]["observation_date"]),
        "average_dollar_volume_usd": fmean(dollar_volumes),
        "distinct_session_count_available": len(selected),
        "same_date_revision_session_count": duplicate_session_count,
        "same_date_revision_policy": "LATEST_COLLECTED_AT_UTC_THEN_SOURCE_RUN_ID",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument(
        "--output",
        default="data/operations/metals/vehicle_liquidity_v1/adv_rehearsal.json",
    )
    args = parser.parse_args()

    root = Path(args.artifact_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"Metals artifact root is missing: {root}")
    price_history = _find_price_history(root)
    rows = _load_rows(price_history)
    vehicles = [_calculate_adv(rows, ticker) for ticker in EXPECTED_TICKERS]

    evidence = {
        "status": "METALS_VEHICLE_ADV_V1_REHEARSAL_PASS",
        "authority_id": "UIP_NATIVE_METALS_VEHICLE_LIQUIDITY_V1",
        "source_authority": SOURCE_AUTHORITY,
        "registered_vehicle_count": len(EXPECTED_TICKERS),
        "adv_complete_vehicle_count": len(vehicles),
        "window_sessions": WINDOW_SESSIONS,
        "formula": "mean(close_usd * volume) over latest 30 distinct trading sessions",
        "vehicles": vehicles,
        "adv_evidence_complete": True,
        "quoted_spread_evidence_complete": False,
        "preferred_vehicle_ranking_ready": False,
        "preferred_vehicle_ranking_state": "FAIL_CLOSED_MISSING_QUOTED_SPREAD_AND_OTHER_REQUIRED_EVIDENCE",
        "network_collection_performed": False,
        "publication_write_performed": False,
        "ranking_created": False,
        "automatic_execution_authorized": False,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

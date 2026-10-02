"""Prepare inputs for the Metals vehicle evidence refresh.

Two small conversions the refresh workflow needs:

* spread: the Alpaca spread rehearsal output (per_ticker medians) becomes the
  committed spread evidence file the ranking reads, using the current file as a
  template. It is marked certified only if every registered vehicle has a positive
  median over at least the required number of sessions.
* commodity state: the Metals tactical-state sidecar becomes the per-metal
  {recommendation, tactical_state, adjusted_expected_return_12m} the ranking
  evidence builder needs.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "metals" / "vehicles.json"
SPREAD_PATH = ROOT / "config" / "presentation" / "metals_vehicle_spread_evidence_v1.json"
DOUBLED_PREFIX = "metals:commodity:metals:commodity:"


def registered_tickers(path: Path = REGISTRY_PATH) -> list[str]:
    registry = json.loads(path.read_text(encoding="utf-8-sig"))
    return [
        str(row["ticker"]).strip().upper()
        for row in registry.get("vehicles", [])
        if row.get("enabled", True) and row.get("role") != "reserve"
    ]


def spread_evidence(alpaca: dict, template: dict, tickers: list[str], source: dict) -> dict:
    per_ticker = {str(key).upper(): value for key, value in (alpaca.get("per_ticker") or {}).items()}
    minimum = int(template.get("minimum_distinct_sessions_required") or 20)
    vehicles: dict[str, dict] = {}
    problems: list[str] = []
    for ticker in tickers:
        row = per_ticker.get(ticker) or {}
        median = row.get("median_relative_bid_ask_spread_bps")
        sessions = int(row.get("distinct_session_count") or 0)
        if median is None or float(median) <= 0:
            problems.append(f"{ticker}: no positive median spread")
            continue
        if sessions < minimum:
            problems.append(f"{ticker}: {sessions} sessions < {minimum}")
            continue
        vehicles[ticker] = {"median_bid_ask_spread_bps": float(median)}
    if problems:
        raise ValueError("spread evidence incomplete: " + "; ".join(problems))
    firsts = [str(per_ticker[t].get("first_session")) for t in tickers if per_ticker[t].get("first_session")]
    lasts = [str(per_ticker[t].get("last_session")) for t in tickers if per_ticker[t].get("last_session")]
    document = copy.deepcopy(template)
    document["vehicles"] = vehicles
    document["first_session"] = min(firsts) if firsts else document.get("first_session")
    document["last_session"] = max(lasts) if lasts else document.get("last_session")
    document["required_ticker_count"] = len(tickers)
    document["resolved_ticker_count"] = len(vehicles)
    document["spread_evidence_certified"] = True
    for key in ("source_run_id", "source_head_sha", "artifact_id", "artifact_digest"):
        if key in source:
            document[key] = source[key]
    return document


def _canonical_commodity_id(raw: str) -> str:
    text = str(raw or "").strip().lower()
    if text.startswith(DOUBLED_PREFIX):
        text = "metals:commodity:" + text[len(DOUBLED_PREFIX):]
    return text


def commodity_state(rows: list[dict]) -> dict[str, dict]:
    state: dict[str, dict] = {}
    for row in rows:
        horizon = str(row.get("tactical_horizon_months", "12")).strip()
        if horizon not in ("12", "12.0"):
            continue
        commodity_id = _canonical_commodity_id(row.get("universal_asset_id", ""))
        if not commodity_id.startswith("metals:commodity:"):
            continue
        if commodity_id in state:
            raise ValueError(f"more than one 12-month tactical row for {commodity_id}")
        adjusted = row.get("adjusted_expected_return")
        state[commodity_id] = {
            "recommendation": str(row.get("recommendation", "")).strip().upper(),
            "tactical_state": str(row.get("tactical_state", "")).strip().upper(),
            "adjusted_expected_return_12m": None if adjusted in (None, "") else float(adjusted),
        }
    if not state:
        raise ValueError("no 12-month commodity rows in the tactical-state file")
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alpaca-evidence", type=Path)
    parser.add_argument("--spread-output", type=Path)
    parser.add_argument("--source", type=Path, help="JSON source binding for the spread evidence")
    parser.add_argument("--tactical-csv", type=Path)
    parser.add_argument("--commodity-state-output", type=Path)
    args = parser.parse_args(argv)

    if args.alpaca_evidence:
        alpaca = json.loads(args.alpaca_evidence.read_text(encoding="utf-8-sig"))
        template = json.loads(SPREAD_PATH.read_text(encoding="utf-8-sig"))
        source = json.loads(args.source.read_text(encoding="utf-8-sig")) if args.source else {}
        document = spread_evidence(alpaca, template, registered_tickers(), source)
        output = args.spread_output or SPREAD_PATH
        output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"SPREAD EVIDENCE: {len(document['vehicles'])} vehicles, "
              f"{document['first_session']} .. {document['last_session']}")
    if args.tactical_csv:
        with args.tactical_csv.open(newline="", encoding="utf-8-sig") as handle:
            state = commodity_state(list(csv.DictReader(handle)))
        args.commodity_state_output.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        for commodity_id, item in sorted(state.items()):
            print(f"  {commodity_id}: {item['recommendation']} / {item['tactical_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

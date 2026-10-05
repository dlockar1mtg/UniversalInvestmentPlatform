"""Project Secret Lair model v2 decisions as MTG premium research records.

The MTG repository scores every Secret Lair daily (scripts/build_secret_lair_v2_decisions.py):
buy when a reliable listing is at least 10% below the market price and the expected 6-month
return after selling costs is positive. This projection publishes one research record per Secret
Lair asset in the MTG export, replacing the August 2026 certified analysis when enabled. Products
v2 did not score are published as NO_PRICE rather than left out, so the record count follows the
asset universe. Nothing is recalculated here; decisions are validated, then copied.
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from .publication_model import PresentationRecord

RECORD_TYPE = "mtg_premium_research"
DOMAIN_ID = "mtg"
LANE = "SECRET_LAIR_V1_1"
RESEARCH_MODEL = "secret-lair-v2"
CALLS = {"BUY", "WAIT", "NO_PRICE"}
REQUIRED_COLUMNS = (
    "secret_lair_id", "product_name", "as_of", "market_price", "buy_price", "buy_price_basis", "gap",
    "expected_return_6m", "expected_net_return_6m", "call", "note", "rank", "ranked_products", "model_version",
)
COPIED = REQUIRED_COLUMNS[2:]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_decisions(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    rows = _read_csv(path)
    if not rows:
        raise RuntimeError(f"Secret Lair v2 decisions are empty: {path}")
    missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
    if missing:
        raise RuntimeError(f"Secret Lair v2 decisions lack columns: {missing}")
    summary_path = path.with_suffix(".json")
    if not summary_path.is_file():
        raise RuntimeError(f"Secret Lair v2 summary is missing: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    buy_gap = float(summary["buy_gap"])
    decisions: dict[str, dict[str, str]] = {}
    for row in rows:
        product, call = row["secret_lair_id"].strip(), row["call"].strip()
        if call not in CALLS:
            raise RuntimeError(f"Unknown Secret Lair v2 call {call!r} for {product}")
        if call == "BUY":
            gap, net = _number(row["gap"]), _number(row["expected_net_return_6m"])
            if gap is None or net is None or gap < buy_gap or net <= 0:
                raise RuntimeError(f"BUY for {product} does not meet the v2 rule (gap {gap}, net {net})")
        if product in decisions:
            raise RuntimeError(f"Duplicate Secret Lair v2 decision for {product}")
        decisions[product] = row
    return decisions, summary


def build_secret_lair_v2_records(decisions_path: Path, export_path: Path, *, today: date | None = None) -> list[PresentationRecord]:
    decisions, summary = load_decisions(decisions_path)
    history_path = decisions_path.with_name("secret_lair_v2_history.json")
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.is_file() else {}
    assets = [r for r in _read_csv(export_path) if r.get("mtg_lane", "").strip() == LANE]
    if not assets:
        raise RuntimeError("The MTG export has no Secret Lair assets")
    as_of = str(summary.get("as_of", ""))
    try:
        age_days = ((today or date.today()) - date.fromisoformat(as_of[:10])).days
    except ValueError:
        age_days = None
    calibration = summary.get("calibration", {})
    records = []
    for asset in assets:
        product = asset["native_asset_id"].strip()
        decision = decisions.get(product)
        payload: dict[str, Any] = {
            "mtg_asset_id": asset["mtg_asset_id"].strip(),
            "secret_lair_id": product,
            "product_name": (decision or {}).get("product_name") or asset.get("product_name", ""),
            "research_model": RESEARCH_MODEL,
            "tcgplayer_product_id": str((decision or {}).get("tcgplayer_product_id") or "").strip(),
            "price_history": list(history.get(product, []))[-36:],
            "price_age_days": age_days,
            "calibration_intercept": calibration.get("intercept"),
            "calibration_slope": calibration.get("slope"),
            "calibration_pairs": calibration.get("pairs"),
            "sell_cost": summary.get("sell_cost"),
            "buy_gap": summary.get("buy_gap"),
            "horizon_months": summary.get("horizon_months"),
        }
        if decision:
            payload.update({field: decision.get(field, "") for field in COPIED})
        else:
            payload.update({field: "" for field in COPIED})
            payload.update({"call": "NO_PRICE", "note": "NOT_IN_DAILY_PRICE_FEED", "as_of": as_of})
        records.append(PresentationRecord(record_type=RECORD_TYPE, domain_id=DOMAIN_ID, asset_id=payload["mtg_asset_id"],
                                          record_key=payload["mtg_asset_id"], payload=payload))
    return records

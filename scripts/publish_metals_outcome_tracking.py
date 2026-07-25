from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from foundation.production.metals_outcome_tracking import (
    MetalsOutcomeObservation,
    evaluate_metals_outcomes,
    publish_metals_outcomes,
    summarize_metals_outcomes,
)

INPUT_PATH = REPO_ROOT / "data" / "operations" / "metals" / "outcome_tracking_input.csv"
OUTPUT_ROOT = REPO_ROOT / "data" / "operations" / "metals" / "outcome_tracking"


def _load() -> tuple[MetalsOutcomeObservation, ...]:
    if not INPUT_PATH.exists():
        return ()
    with INPUT_PATH.open(newline="", encoding="utf-8") as handle:
        return tuple(MetalsOutcomeObservation(
            forecast_id=row["forecast_id"],
            asset_id=row["asset_id"],
            vehicle_ticker=row["vehicle_ticker"],
            horizon_days=int(row["horizon_days"]),
            forecast_return_pct=float(row["forecast_return_pct"]),
            forecast_probability_up=float(row["forecast_probability_up"]),
            recommendation=row["recommendation"],
            signal_price=float(row["signal_price"]),
            realized_price=float(row["realized_price"]),
            benchmark_return_pct=float(row["benchmark_return_pct"]),
            regime=row["regime"],
            portfolio_weight_pct=float(row["portfolio_weight_pct"]),
            estimated_slippage_pct=float(row["estimated_slippage_pct"]),
        ) for row in csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    observations = _load()
    rows = evaluate_metals_outcomes(observations)
    summary = summarize_metals_outcomes(rows)
    publish_metals_outcomes(rows, summary, OUTPUT_ROOT)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(f"METALS OUTCOME TRACKING: {summary['status']}")
    print(f"Outcomes: {summary['outcome_count']}")
    print(f"Output: {OUTPUT_ROOT}")
    if args.strict and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from foundation.production.metals_risk_aware_constraints import (
    MetalsVehicleRiskInput,
    evaluate_vehicle_constraints,
    publish_vehicle_constraints,
    summarize_vehicle_constraints,
)

DEFAULT_INPUT = REPO_ROOT / "data" / "operations" / "metals" / "risk_aware_constraints_input.csv"
POLICY_PATH = REPO_ROOT / "config" / "metals" / "risk_aware_vehicle_constraints.json"
OUTPUT_ROOT = REPO_ROOT / "data" / "operations" / "metals" / "risk_aware_constraints"


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _load(path: Path) -> tuple[MetalsVehicleRiskInput, ...]:
    if not path.exists():
        return ()
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(
            MetalsVehicleRiskInput(
                asset_id=row["asset_id"],
                vehicle_ticker=row["vehicle_ticker"],
                approved=_as_bool(row["approved"]),
                metadata_current=_as_bool(row["metadata_current"]),
                average_daily_volume=float(row["average_daily_volume"]),
                spread_pct=float(row["spread_pct"]),
                expense_ratio_pct=float(row["expense_ratio_pct"]),
                roll_drag_pct=float(row["roll_drag_pct"]),
                miner_beta=float(row["miner_beta"]),
                single_company_concentration_pct=float(row["single_company_concentration_pct"]),
                single_country_concentration_pct=float(row["single_country_concentration_pct"]),
                currency_exposure_pct=float(row["currency_exposure_pct"]),
                tax_structure=row["tax_structure"],
                overlap_pct=float(row["overlap_pct"]),
                factor_exposure_score=float(row["factor_exposure_score"]),
            )
            for row in csv.DictReader(handle)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))["policy"]
    rows = evaluate_vehicle_constraints(_load(args.input), policy)
    summary = summarize_vehicle_constraints(rows)
    publish_vehicle_constraints(rows, summary, OUTPUT_ROOT)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(f"METALS RISK-AWARE CONSTRAINTS: {summary['status']}")
    print(f"Vehicles: {summary['vehicle_count']}")
    print(f"Eligible: {summary['eligible_count']}")
    print(f"Capped: {summary['capped_count']}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Input: {args.input.resolve()}")
    print(f"Output: {OUTPUT_ROOT}")

    if args.strict and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

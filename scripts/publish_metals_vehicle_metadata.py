"""Publish Metals vehicle metadata completeness and freshness outputs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_vehicle_metadata import (  # noqa: E402
    build_vehicle_metadata_dataset,
    load_market_metadata,
    load_structural_metadata,
    summarize_vehicle_metadata,
    write_vehicle_metadata_outputs,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Metals vehicle metadata status.")
    parser.add_argument(
        "--structural-metadata",
        type=Path,
        default=ROOT / "config" / "metals" / "vehicle_structural_metadata.json",
    )
    parser.add_argument(
        "--market-metadata",
        type=Path,
        default=ROOT / "config" / "metals" / "vehicle_market_metadata.csv",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "vehicle_metadata",
    )
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a nonzero exit code unless every registered vehicle is complete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    structural = load_structural_metadata(args.structural_metadata)
    market = load_market_metadata(args.market_metadata)
    rows = build_vehicle_metadata_dataset(structural, market, as_of=args.as_of)
    summary = summarize_vehicle_metadata(rows)
    write_vehicle_metadata_outputs(rows, summary, args.output_root)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(f"METALS VEHICLE METADATA: {summary['status']}")
    print(f"Vehicles: {summary['vehicle_count']}")
    print(f"Complete: {summary['complete_vehicle_count']}")
    print(f"Eligible: {summary['eligible_vehicle_count']}")
    print(f"Output: {args.output_root.resolve()}")
    if args.strict and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

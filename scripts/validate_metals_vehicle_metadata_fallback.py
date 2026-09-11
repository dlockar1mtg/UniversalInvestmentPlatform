"""Validate an existing Metals vehicle metadata snapshot for bounded provider-degradation fallback use."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_registry import load_metals_registry  # noqa: E402
from foundation.production.metals_vehicle_metadata import (  # noqa: E402
    MetalsVehicleMetadataError,
    build_vehicle_metadata_dataset,
    load_market_metadata,
    load_structural_metadata,
    summarize_vehicle_metadata,
)

ALLOWED_FALLBACK_REASONS = (
    "YAHOO_RATE_LIMIT",
    "YAHOO_INCOMPLETE_METADATA_RESPONSE",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an existing Metals metadata snapshot for bounded provider-degradation fallback."
    )
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
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--fallback-reason",
        choices=ALLOWED_FALLBACK_REASONS,
        default="YAHOO_RATE_LIMIT",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    registry = load_metals_registry(ROOT / "config" / "metals")
    structural = load_structural_metadata(args.structural_metadata)
    market = load_market_metadata(args.market_metadata)

    registry_tickers = set(registry.vehicles_by_ticker)
    structural_tickers = set(structural)
    market_tickers = set(market)
    if structural_tickers != registry_tickers:
        raise MetalsVehicleMetadataError(
            "fallback structural metadata must exactly cover the canonical Metals registry"
        )
    if market_tickers != registry_tickers:
        missing = sorted(registry_tickers - market_tickers)
        extra = sorted(market_tickers - registry_tickers)
        raise MetalsVehicleMetadataError(
            f"fallback market metadata must exactly cover the canonical registry; missing={missing}, extra={extra}"
        )

    rows = build_vehicle_metadata_dataset(structural, market, as_of=args.as_of)
    summary = summarize_vehicle_metadata(rows)
    stale = summary["freshness_counts"].get("STALE", 0)
    missing = summary["freshness_counts"].get("MISSING", 0)
    complete = summary["complete_vehicle_count"] == summary["vehicle_count"]
    valid = bool(rows) and complete and stale == 0 and missing == 0

    ages = [row["metadata_age_days"] for row in rows if row["metadata_age_days"] is not None]
    evidence = {
        "status": "METALS_VEHICLE_METADATA_FALLBACK_PASS" if valid else "FAIL_CLOSED",
        "as_of": args.as_of.isoformat(),
        "vehicle_count": summary["vehicle_count"],
        "complete_vehicle_count": summary["complete_vehicle_count"],
        "freshness_counts": summary["freshness_counts"],
        "maximum_metadata_age_days": max(ages) if ages else None,
        "fallback_reason": args.fallback_reason,
        "fallback_reasons_allowed": list(ALLOWED_FALLBACK_REASONS),
        "network_collection_performed_by_validator": False,
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

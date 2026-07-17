"""Validate the Phase 2.5 Contribution and Rebalancing Engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.validation import (
    validate_contribution_rebalancing_database,
)

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    result = validate_contribution_rebalancing_database(args.database.resolve())
    print("Contribution and Rebalancing Engine Validation")
    print("=" * 72)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")

    if result.is_valid:
        print("Result: VALID")
        return 0
    print(f"Result: INVALID ({len(result.errors)} error(s))")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

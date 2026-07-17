"""Validate the Phase 2.1 universal portfolio domain configuration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.validation import validate_portfolio_configuration


def main() -> int:
    result = validate_portfolio_configuration(ROOT / "config" / "portfolios")

    print("Universal Portfolio Domain Validation")
    print("=" * 72)

    for warning in result.warnings:
        print(f"WARNING: {warning}")

    for error in result.errors:
        print(f"ERROR: {error}")

    if result.is_valid:
        print("Result: VALID")
        print("Allocation targets total 100%.")
        return 0

    print(f"Result: INVALID ({len(result.errors)} error(s))")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

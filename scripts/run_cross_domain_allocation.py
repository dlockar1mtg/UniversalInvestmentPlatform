from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.intelligence.cross_domain import AllocationPolicy, load_domain_package, write_allocation_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Allocate monthly investment capital across certified domain packages")
    parser.add_argument("--domain-package", type=Path, action="append", required=True)
    parser.add_argument("--monthly-budget", type=float, required=True)
    parser.add_argument("--minimum-deployment-score", type=float, default=55.0)
    parser.add_argument("--maximum-domain-weight-pct", type=float, default=100.0)
    parser.add_argument("--minimum-cash-reserve-pct", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.monthly_budget < 0:
        raise SystemExit("Monthly budget cannot be negative")
    packages = [load_domain_package(path) for path in args.domain_package]
    payload = write_allocation_plan(
        args.output,
        packages,
        AllocationPolicy(
            monthly_budget=args.monthly_budget,
            minimum_deployment_score=args.minimum_deployment_score,
            maximum_domain_weight_pct=args.maximum_domain_weight_pct,
            minimum_cash_reserve_pct=args.minimum_cash_reserve_pct,
        ),
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

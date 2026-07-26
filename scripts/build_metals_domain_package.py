from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.intelligence.cross_domain.adapters.metals import write_metals_domain_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a certified Metals universal package into a UIP domain package.")
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--allocation-ceiling", type=float, required=True)
    parser.add_argument("--minimum-deployment-score", type=float, default=55.0)
    parser.add_argument("--allocation-increment", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = write_metals_domain_package(
        args.package_root,
        args.output,
        allocation_ceiling=args.allocation_ceiling,
        minimum_deployment_score=args.minimum_deployment_score,
        allocation_increment=args.allocation_increment,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("domain_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

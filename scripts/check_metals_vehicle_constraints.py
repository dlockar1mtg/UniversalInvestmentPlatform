"""Exercise representative Metals vehicle constraints without market-data access."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from foundation.production.metals_vehicles import (  # noqa: E402
    VehicleCandidate,
    select_metals_vehicles,
)


CASES = {
    "gold": (("GLD", 95), ("IAU", 70), ("SGOL", 65)),
    "silver": (("SLV", 85), ("SIVR", 65)),
    "copper": (("COPX", 95), ("CPER", 30)),
    "uranium": (("URA", 90), ("URNM", 50)),
    "platinum": (("PPLT", 75),),
    "tactical_reserve": (("BIL", 80),),
}


def main() -> int:
    checks = []
    for asset_slug, values in CASES.items():
        result = select_metals_vehicles(
            asset_slug,
            [VehicleCandidate(ticker, score) for ticker, score in values],
        )
        checks.append(
            {
                "asset": asset_slug,
                "total_share_pct": str(result.total_share_pct),
                "direct_share_pct": str(result.direct_share_pct),
                "miner_share_pct": str(result.miner_share_pct),
                "allocations": [
                    {
                        "ticker": item.ticker,
                        "score": str(item.score),
                        "share_pct": str(item.share_pct),
                    }
                    for item in result.allocations
                ],
                "status": "PASS",
            }
        )
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from foundation.production.metals_industrial_vehicle_coverage import (
    publish_industrial_vehicle_coverage,
    summarize_industrial_vehicle_coverage,
    validate_industrial_vehicle_coverage,
)


CONFIG_PATH = REPO_ROOT / "config" / "metals" / "industrial_vehicle_coverage.json"
OUTPUT_ROOT = REPO_ROOT / "data" / "operations" / "metals" / "industrial_vehicle_coverage"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    document = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    rows = validate_industrial_vehicle_coverage(document)
    summary = summarize_industrial_vehicle_coverage(rows)
    publish_industrial_vehicle_coverage(rows, summary, OUTPUT_ROOT)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(f"METALS INDUSTRIAL VEHICLE COVERAGE: {summary['status']}")
    print(f"Metals: {summary['metal_count']}")
    print(f"Eligible: {summary['eligible_metal_count']}")
    print(f"Research only: {summary['research_only_count']}")
    print(f"Blocked: {summary['blocked_metal_count']}")
    print(f"Output: {OUTPUT_ROOT}")

    if args.strict and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

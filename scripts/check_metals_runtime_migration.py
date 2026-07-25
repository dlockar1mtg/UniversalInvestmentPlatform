"""Publish Metals runtime-migration readiness evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_runtime_migration import (  # noqa: E402
    evaluate_contract,
    load_contract,
    publish_report,
)

DEFAULT_CONTRACT = ROOT / "config" / "metals" / "runtime_migration_contract.json"
DEFAULT_OUTPUT = ROOT / "data" / "operations" / "metals" / "runtime_migration" / "latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Metals runtime migration readiness.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = evaluate_contract(load_contract(args.contract), ROOT)
    publish_report(report, args.output)
    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nMETALS RUNTIME MIGRATION: {report.status}")
    print(f"Implemented: {report.implemented_count}/{report.capability_count}")
    print(f"Planned: {report.planned_count}")
    print(f"Output: {args.output.resolve()}")
    return 1 if args.strict and report.status != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())

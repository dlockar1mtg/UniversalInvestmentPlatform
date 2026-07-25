"""Publish Metals legacy-retirement verification evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from foundation.production.metals_legacy_retirement import (
    evaluate_retirement_evidence,
    load_retirement_evidence,
    publish_retirement_result,
)

DEFAULT_INPUT = REPO_ROOT / "data" / "operations" / "metals" / "legacy_retirement_evidence.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "operations" / "metals" / "legacy_retirement_verification"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.input.exists():
        document = load_retirement_evidence(args.input)
    else:
        document = {}

    result = evaluate_retirement_evidence(document)
    publish_retirement_result(result, args.output_dir)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print()
    print(f"METALS LEGACY RETIREMENT: {result.status}")
    print(f"Legacy system: {result.legacy_system_name or 'UNKNOWN'}")
    print(f"Runtime executions: {result.legacy_runtime_execution_count}")
    print(f"Database accesses: {result.legacy_database_access_count}")
    print(f"Input: {args.input.resolve()}")
    print(f"Output: {args.output_dir.resolve()}")

    if args.strict and result.status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

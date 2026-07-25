"""Evaluate the standalone-free UIP-native Metals package."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from foundation.production.metals_native_readiness import evaluate_native_readiness, publish_native_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "operations" / "metals" / "native_readiness" / "latest.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = evaluate_native_readiness(args.package_root)
    publish_native_readiness(report, args.output)
    print(json.dumps(report.to_dict(), indent=2))
    print(f"METALS NATIVE READINESS: {report.status}")
    return 1 if args.strict and report.status != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())

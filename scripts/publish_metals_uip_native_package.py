"""Publish a Universal Metals package from UIP-native forecast output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from exchange.metals.adapter.uip_native import publish_uip_native_metals_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-cycle", type=Path, default=ROOT / "data" / "operations" / "metals" / "native_cycle" / "latest.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "integration" / "metals" / "uip_native_packages")
    parser.add_argument("--run-id")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        result = publish_uip_native_metals_package(args.native_cycle, args.output_root, run_id=args.run_id)
    except Exception as exc:
        print(f"METALS UIP-NATIVE PACKAGE: FAILED\n{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    print(json.dumps(result.to_dict(), indent=2))
    print("METALS UIP-NATIVE PACKAGE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

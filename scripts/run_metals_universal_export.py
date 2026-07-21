from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from exchange.metals.adapter import build_package


def main() -> int:
    parser=argparse.ArgumentParser(description="Build the Metals Universal v1 export package.")
    parser.add_argument("--metals-root", type=Path, required=True, help="Path to the standalone Metals repository.")
    parser.add_argument("--universal-root", type=Path, default=ROOT, help="Universal Investment Platform repository root.")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--schema-root", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--allow-legacy-database-fallback",
        action="store_true",
        help="Explicitly permit read-only DuckDB access when verified bridge exports are absent.",
    )
    args=parser.parse_args()
    try:
        package=build_package(args.universal_root,args.metals_root,args.output_root,args.config,args.schema_root,args.allow_legacy_database_fallback)
    except Exception as exc:
        print(f"METALS UNIVERSAL EXPORT: FAILED\n{exc}",file=sys.stderr)
        return 1
    print("METALS UNIVERSAL EXPORT: PASS")
    print(f"Package: {package}")
    return 0


if __name__ == "__main__": raise SystemExit(main())

"""Run one or all UIP-governed production platforms."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.control_plane import (
    SUPPORTED_PLATFORMS,
    load_control_plane_config,
    run_unified_cycle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the UIP unified production control plane.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "production_control_plane.local.json",
    )
    parser.add_argument(
        "--platforms",
        default="all",
        help="Comma-separated metals,mtg,crypto or all.",
    )
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()

    selected = (
        list(SUPPORTED_PLATFORMS)
        if args.platforms.strip().lower() == "all"
        else [item.strip().lower() for item in args.platforms.split(",") if item.strip()]
    )
    try:
        config = load_control_plane_config(args.config)
        result = run_unified_cycle(
            config,
            selected,
            continue_on_failure=args.continue_on_failure,
        )
    except Exception as exc:
        print("UIP UNIFIED PRODUCTION CYCLE: FAILED")
        print(str(exc))
        return 1

    print(json.dumps(asdict(result), indent=2))
    print(f"UIP UNIFIED PRODUCTION CYCLE: {result.status}")
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the governed MTG-to-UIP manual production cycle."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from foundation.integrations.mtg.manual_production import (
    run_mtg_manual_production_cycle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run MTG production, validate the Phase 11E.17 handoff and package, "
            "import it transactionally, then publish UIP-owned datasets."
        )
    )
    parser.add_argument(
        "--mtg-root",
        type=Path,
        default=REPOSITORY_ROOT.parent / "mtg-investment-terminal",
        help="Path to the standalone MTG repository.",
    )
    parser.add_argument(
        "--skip-source-run",
        action="store_true",
        help="Use the existing handoff without invoking the MTG production command.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_mtg_manual_production_cycle(
            REPOSITORY_ROOT,
            args.mtg_root,
            skip_source_run=args.skip_source_run,
        )
    except Exception as exc:
        print("MTG UIP PRODUCTION CYCLE: FAILED")
        print(str(exc))
        return 1

    print(json.dumps(asdict(result), indent=2))
    print("MTG UIP PRODUCTION CYCLE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

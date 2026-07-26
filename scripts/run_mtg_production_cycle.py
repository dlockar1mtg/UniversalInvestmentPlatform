"""Run the isolated Phase 10.12 MTG production foundation."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.mtg.cycle import MTGProductionCycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("../mtg-source"))
    parser.add_argument("--config", type=Path, default=Path("config/mtg/production.json"))
    parser.add_argument("--output-root", type=Path, default=Path("data/operations/mtg/production_cycle"))
    parser.add_argument("--run-id", default="local-safe-hold")
    args = parser.parse_args()

    report = MTGProductionCycle(args.source_root, args.config, args.output_root).run(
        run_id=args.run_id,
        environment=os.environ,
    )
    print(f"MTG production status: {report.status}")
    print(f"Mode: {report.mode}")
    print("Reason codes: " + ", ".join(report.reason_codes))
    return 0 if report.status in {"SAFE_HOLD", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

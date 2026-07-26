"""Validate isolated MTG production governance contracts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.mtg.contracts import validate_mtg_contracts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-root", type=Path, default=Path("config/mtg"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = validate_mtg_contracts(args.config_root)
    print(f"MTG contract status: {result.status}")
    for reason in result.reason_codes:
        print(f"- {reason}")
    return 0 if result.passed or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())

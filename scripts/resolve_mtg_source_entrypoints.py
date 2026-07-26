"""Resolve authoritative MTG source entry points from the static audit report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.mtg.entrypoints import (  # noqa: E402
    load_audit,
    publish_entrypoints,
    resolve_entrypoints,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path("data/operations/mtg/source_audit/latest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/operations/mtg/source_entrypoints/latest.json"),
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = resolve_entrypoints(load_audit(args.audit))
    publish_entrypoints(report, args.output)
    print(f"MTG entrypoint status: {report.status}")
    for role, candidate in sorted(report.selections.items()):
        print(f"- {role}: {candidate.path}")
    print("Reason codes: " + ", ".join(report.reason_codes))
    return 1 if args.strict and report.status != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())

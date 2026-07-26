"""Audit the local MTG source checkout without executing source code or APIs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.mtg.source_audit import audit_source, publish_source_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("../mtg-source"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/operations/mtg/source_audit/latest.json"),
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = audit_source(args.source_root)
    publish_source_audit(report, args.output)
    print(f"MTG source audit status: {report.status}")
    print(f"Files scanned: {report.files_scanned}")
    for capability, count in sorted(report.capability_counts.items()):
        print(f"- {capability}: {count}")
    print("Reason codes: " + ", ".join(report.reason_codes))
    if args.strict and report.status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

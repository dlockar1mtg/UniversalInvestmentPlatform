"""Run and optionally persist the Metals production-readiness dashboard projection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_readiness import evaluate_metals_readiness  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Metals production readiness.")
    parser.add_argument("--metals-root", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--skip-live-providers",
        action="store_true",
        help="Skip external provider calls for an offline diagnostic; not valid for certification.",
    )
    args = parser.parse_args()
    report = evaluate_metals_readiness(
        args.metals_root,
        args.package_root,
        universal_root=ROOT,
        include_live_providers=not args.skip_live_providers,
    )
    document = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document + "\n", encoding="utf-8")
    print(document)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Execute the canonical Metals production cycle and persist structured evidence."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_cycle import default_stages, run_metals_cycle  # noqa: E402
from foundation.production.metals_operations_status import (  # noqa: E402
    build_metals_operations_status,
    write_metals_operations_status,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the canonical Metals production cycle.")
    parser.add_argument("--metals-root", type=Path, required=True)
    parser.add_argument(
        "--package-root",
        type=Path,
        default=ROOT / "data" / "integration" / "metals" / "latest",
    )
    parser.add_argument(
        "--history-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "cycle_history",
    )
    parser.add_argument(
        "--operations-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals",
    )
    parser.add_argument("--owner", default="Devon Lockard")
    parser.add_argument("--notification-destination", default="local-console")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--skip-live-providers", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    package_root = args.package_root.resolve()
    history_root = args.history_root.resolve()
    operations_root = args.operations_root.resolve()
    stages = default_stages(
        ROOT,
        args.metals_root.resolve(),
        package_root,
        skip_export=args.skip_export,
        skip_live_providers=args.skip_live_providers,
    )
    record = run_metals_cycle(
        repository_root=ROOT,
        metals_root=args.metals_root.resolve(),
        package_root=package_root,
        history_root=history_root,
        owner=args.owner,
        notification_destination=args.notification_destination,
        stages=stages,
    )
    status = build_metals_operations_status(
        latest_cycle_path=history_root / "latest.json",
        latest_readiness_path=operations_root / "latest_readiness.json",
    )
    json_path, csv_path = write_metals_operations_status(status, operations_root)

    print(json.dumps(asdict(record), indent=2, sort_keys=True))
    print()
    print(f"METALS PRODUCTION CYCLE: {record.status}")
    print(f"Cycle ID: {record.cycle_id}")
    print(f"Package ID: {record.package_id or 'unavailable'}")
    print(f"Failed stage: {record.failed_stage or 'none'}")
    print(f"Operations JSON: {json_path}")
    print(f"Operations CSV: {csv_path}")
    return 0 if record.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

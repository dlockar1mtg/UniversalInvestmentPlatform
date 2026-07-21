"""Create the one-time verified CSV handoff from the standalone Metals DuckDB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange.metals.adapter.native_surfaces import (  # noqa: E402
    NativeSurfaceError,
    export_bridge_surfaces,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export legacy-only Metals views into a verified file handoff."
    )
    parser.add_argument(
        "--metals-root",
        type=Path,
        required=True,
        help="Path to the standalone Metals v8 project.",
    )
    args = parser.parse_args()
    try:
        manifest = export_bridge_surfaces(args.metals_root)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except NativeSurfaceError as exc:
        print(f"METALS BRIDGE EXPORT: FAILED\n{exc}", file=sys.stderr)
        return 1
    print("METALS BRIDGE EXPORT: PASS")
    print(f"Manifest: {manifest}")
    print(f"Surfaces: {len(payload['surfaces'])}")
    print(f"Records: {sum(item['row_count'] for item in payload['surfaces'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

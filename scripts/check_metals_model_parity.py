"""Certify Metals model evidence and universal transformation parity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exchange.metals.adapter.parity import (  # noqa: E402
    MetalsParityError,
    certify_metals_parity,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify Metals model and export parity.")
    parser.add_argument("--metals-root", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = certify_metals_parity(args.metals_root, args.package_root)
    except (MetalsParityError, FileNotFoundError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)},
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

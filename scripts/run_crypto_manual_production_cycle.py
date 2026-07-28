"""Run the complete Crypto-to-UIP production cycle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.integrations.crypto import run_crypto_production_cycle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the governed Crypto production cycle and UIP import."
    )
    parser.add_argument(
        "--crypto-root",
        type=Path,
        required=True,
        help="Path to the standalone CryptoIntelligencePlatform repository.",
    )
    parser.add_argument(
        "--skip-source-run",
        action="store_true",
        help="Use the most recent Crypto production run and prepared delivery.",
    )
    args = parser.parse_args()

    try:
        result = run_crypto_production_cycle(
            ROOT,
            args.crypto_root,
            skip_source_run=args.skip_source_run,
        )
    except Exception as exc:
        print("CRYPTO UIP PRODUCTION CYCLE: FAILED")
        print(str(exc))
        return 1

    print(json.dumps(result.__dict__, indent=2))
    print("CRYPTO UIP PRODUCTION CYCLE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

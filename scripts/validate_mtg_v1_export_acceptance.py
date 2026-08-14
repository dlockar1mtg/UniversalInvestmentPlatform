"""Run UIP-MTG-A1 acceptance against governed MTG artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.integrations.mtg.v1_export_acceptance import (
    accept_mtg_v1_export,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--portability", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    result = accept_mtg_v1_export(
        payload_path=args.payload,
        manifest_path=args.manifest,
        schema_contract_path=args.schema,
        export_contract_path=args.contract,
        portability_correction_path=args.portability,
        report_path=args.report,
    )

    print(
        json.dumps(
            asdict(result),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

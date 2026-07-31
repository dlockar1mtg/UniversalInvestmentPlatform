"""Import one certified MTG delivery through the UIP intake boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.mtg_intake import (
    intake_certified_mtg_package,
    result_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize and import a certified MTG delivery "
            "without invoking standalone MTG production."
        )
    )

    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--package",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--validation-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--result-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--force",
        action="store_true",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    result = intake_certified_mtg_package(
        repository_root=args.repo,
        source_package=args.package,
        database_path=args.database,
        workspace_root=args.workspace_root,
        validation_root=args.validation_root,
        result_root=args.result_root,
        force=args.force,
    )

    print(
        json.dumps(
            result_to_dict(result),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

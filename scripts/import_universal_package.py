"""Import a Universal Integration Package into Universal DuckDB."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.loader import import_package


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a Universal Integration Package."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to a Universal Integration Package directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow a controlled reimport of an existing package.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    initialize_database(config)

    package_path = Path(args.package)
    if not package_path.is_absolute():
        package_path = REPOSITORY_ROOT / package_path

    try:
        result = import_package(
            config=config,
            package_path=package_path,
            force=args.force,
        )
    except DuplicatePackageError as exc:
        print("UNIVERSAL PACKAGE IMPORT: REJECTED")
        print(str(exc))
        return 2
    except Exception as exc:
        print("UNIVERSAL PACKAGE IMPORT: FAILED")
        print(str(exc))
        return 1

    print("=" * 72)
    print("Universal Integration Package Import")
    print("=" * 72)
    print(f"Package ID: {result.package_id}")
    print(f"Platform: {result.platform_id}")
    print(f"Import ID: {result.import_id}")
    print(f"Datasets imported: {len(result.dataset_results)}")
    print(f"Rows imported: {result.imported_row_count}")
    print()

    for dataset in result.dataset_results:
        print(
            f"IMPORTED {dataset.dataset_name:<25} "
            f"rows={dataset.imported_row_count}"
        )

    print()
    print("UNIVERSAL PACKAGE IMPORT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

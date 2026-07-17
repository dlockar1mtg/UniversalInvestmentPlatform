"""Discover and validate a Universal Integration Package."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.package import discover_package
from foundation.import_engine.reports import write_validation_report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Universal Integration Package."
    )

    parser.add_argument(
        "--package",
        required=True,
        help="Path to the Universal Integration Package directory.",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Validate without writing evidence files.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    config.ensure_directories()

    package_path = Path(args.package)

    if not package_path.is_absolute():
        package_path = REPOSITORY_ROOT / package_path

    try:
        package = discover_package(package_path)
        result = validate_package_integrity(package)

        report_path = None

        if not args.no_report:
            report_path = write_validation_report(
                config.validation_root,
                package,
                result,
            )
    except Exception as exc:
        print("UNIVERSAL PACKAGE VALIDATION: FAILED")
        print(str(exc))
        return 1

    print("=" * 72)
    print("Universal Integration Package Validation")
    print("=" * 72)
    print(f"Package: {package.package_path}")
    print(f"Package ID: {package.identity.package_id}")
    print(f"Platform: {package.identity.platform_id}")
    print(f"Run ID: {package.identity.run_id or '(not supplied)'}")
    print(
        f"Adapter version: "
        f"{package.identity.adapter_version or '(not supplied)'}"
    )
    print(
        f"Contract version: "
        f"{package.identity.contract_version or '(not supplied)'}"
    )
    print(f"Files declared: {len(result.file_results)}")
    print(f"Warnings: {result.warning_count}")
    print(f"Errors: {result.error_count}")
    print()

    for file_result in result.file_results:
        print(
            f"{file_result.validation_status:<7} "
            f"{file_result.filename:<35} "
            f"rows={file_result.actual_row_count:<8} "
            f"checksum={file_result.checksum_status}"
        )

        if file_result.error_message:
            print(f"        {file_result.error_message}")

    print()

    if report_path is not None:
        print(f"Evidence: {report_path}")

    if result.passed:
        print("UNIVERSAL PACKAGE VALIDATION: PASS")
        return 0

    print("UNIVERSAL PACKAGE VALIDATION: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
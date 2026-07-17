"""Run the complete Metals-to-Universal pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.audit import (
    apply_audit_registry_migration,
    record_failed_import,
    synchronize_successful_import,
)
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete Metals Universal integration pipeline."
    )
    parser.add_argument(
        "--metals-root",
        required=True,
        help="Path to the standalone Metals repository.",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Use the existing Metals latest package without creating a new export.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)
    initialize_database(config)
    apply_audit_registry_migration(config)

    latest_package = (
        REPOSITORY_ROOT / "data" / "integration" / "metals" / "latest"
    )

    if not args.skip_export:
        export_command = [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts" / "run_metals_universal_export.py"),
            "--metals-root",
            str(Path(args.metals_root).resolve()),
        ]

        print("=" * 72)
        print("Step 1 - Metals Universal Export")
        print("=" * 72)

        completed = subprocess.run(
            export_command,
            cwd=REPOSITORY_ROOT,
            text=True,
        )

        if completed.returncode != 0:
            print("METALS END-TO-END PIPELINE: FAILED")
            print("Metals Universal export failed.")
            return 1

    package = None
    validation = None

    try:
        print()
        print("=" * 72)
        print("Step 2 - Package Discovery and Integrity Validation")
        print("=" * 72)

        package = discover_package(latest_package)
        validation = validate_package_integrity(package)

        print(f"Package ID: {package.identity.package_id}")
        print(f"Platform: {package.identity.platform_id}")
        print(f"Manifest files: {len(package.manifest_entries)}")
        print(f"Integrity warnings: {validation.warning_count}")
        print(f"Integrity errors: {validation.error_count}")

        if not validation.passed:
            raise RuntimeError(
                f"Package integrity validation failed with "
                f"{validation.error_count} error(s)."
            )

        print()
        print("=" * 72)
        print("Step 3 - Transactional Import")
        print("=" * 72)

        result = import_package(
            config=config,
            package_path=latest_package,
        )

        synchronize_successful_import(
            config,
            import_id=result.import_id,
        )

        print(f"Import ID: {result.import_id}")
        print(f"Datasets imported: {len(result.dataset_results)}")
        print(f"Rows imported: {result.imported_row_count}")
        print("Registry synchronization: PASS")

    except Exception as exc:
        try:
            record_failed_import(
                config,
                package=package,
                package_path=latest_package,
                import_mode="END_TO_END",
                error_code="END_TO_END_PIPELINE_FAILURE",
                error_message=str(exc),
                manifest_sha256=(
                    validation.manifest_sha256
                    if validation is not None
                    else ""
                ),
            )
        except Exception as audit_exc:
            print(f"Audit persistence also failed: {audit_exc}")

        print("METALS END-TO-END PIPELINE: FAILED")
        print(str(exc))
        return 1

    print()
    print("METALS END-TO-END PIPELINE: PASS")
    print(f"Package ID: {result.package_id}")
    print(f"Import ID: {result.import_id}")
    print(f"Rows imported: {result.imported_row_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

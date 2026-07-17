"""Certify Phase 1.3.3 package discovery and integrity validation."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.package import discover_package


REQUIRED_PACKAGE_FILES = {
    "export_manifest.csv",
    "platform_status.csv",
}


def main() -> int:
    package_path = (
        REPOSITORY_ROOT
        / "data"
        / "integration"
        / "metals"
        / "latest"
    )

    print("=" * 72)
    print("Phase 1.3.3 - Package Discovery and Integrity Validation")
    print("=" * 72)

    try:
        package = discover_package(package_path)
        result = validate_package_integrity(package)
    except Exception as exc:
        print("CERTIFICATION: FAILED")
        print(str(exc))
        return 1

    package_filenames = {
        path.name
        for path in package.package_path.iterdir()
        if path.is_file()
    }

    missing_required_files = sorted(
        REQUIRED_PACKAGE_FILES - package_filenames
    )

    print(f"Package: {package.package_path}")
    print(f"Package ID: {package.identity.package_id}")
    print(f"Platform: {package.identity.platform_id}")
    print(f"Manifest entries: {len(package.manifest_entries)}")
    print(f"Missing package files: {len(missing_required_files)}")
    print(f"Integrity warnings: {result.warning_count}")
    print(f"Integrity errors: {result.error_count}")

    if missing_required_files:
        print()
        print("Missing required package files:")

        for filename in missing_required_files:
            print(f"  - {filename}")

    if missing_required_files or not result.passed:
        print("CERTIFICATION: FAILED")
        return 1

    print("CERTIFICATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Certify the Phase 1.3.1 Universal Import Engine specification."""

from __future__ import annotations

from pathlib import Path
import sys


REQUIRED_FILES = [
    "foundation/import_engine/__init__.py",
    "foundation/import_engine/config.py",
    "foundation/import_engine/exceptions.py",
    "foundation/import_engine/README.md",
    "foundation/import_engine/docs/UNIVERSAL_PACKAGE_STANDARD.md",
    "foundation/import_engine/docs/IMPORT_POLICY.md",
    "foundation/import_engine/docs/UNIVERSAL_DATABASE_STANDARD.md",
    "foundation/import_engine/docs/PHASE_1_3_ARCHITECTURE.md",
]


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]

    missing = [
        relative_path
        for relative_path in REQUIRED_FILES
        if not (repository_root / relative_path).is_file()
    ]

    print("=" * 72)
    print("Phase 1.3.1 - Universal Import Engine Specification")
    print("=" * 72)

    if missing:
        print("CERTIFICATION: FAILED")
        print()
        print("Missing required files:")

        for path in missing:
            print(f"  - {path}")

        return 1

    print(f"Required files: {len(REQUIRED_FILES)}")
    print("Missing files: 0")
    print("CERTIFICATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
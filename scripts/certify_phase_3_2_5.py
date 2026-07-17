"""Certify Phase 3.2.5 cross-asset validation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/cross_asset_contracts.py",
    "foundation/intelligence/validation/cross_asset_grading.py",
    "foundation/intelligence/validation/cross_asset_engine.py",
    "foundation/intelligence/validation/cross_asset_adapter.py",
    "foundation/intelligence/validation/cross_asset_limitations.py",
    "tests/intelligence/validation/test_cross_asset_grading.py",
    "tests/intelligence/validation/test_cross_asset_engine.py",
    "tests/intelligence/validation/test_cross_asset_limitations.py",
)


def main() -> int:
    root = Path.cwd()
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    if missing:
        print("CERTIFICATION FAILED: Missing required files:")
        for path in missing:
            print(f" - {path}")
        return 1

    commands = (
        [sys.executable, "-m", "pytest", "tests/intelligence/validation", "-q"],
        [sys.executable, "-m", "pytest", "-q"],
    )
    for command in commands:
        print(f"\n> {' '.join(command)}")
        result = subprocess.run(command, cwd=root)
        if result.returncode != 0:
            print("\nPHASE 3.2.5 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.5 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

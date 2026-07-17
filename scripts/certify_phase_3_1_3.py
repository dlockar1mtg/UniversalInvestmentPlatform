"""Certify Phase 3.1.3 composite scoring engine."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/scoring/composite_engine.py",
    "foundation/intelligence/scoring/dimension_aggregation.py",
    "foundation/intelligence/scoring/confidence_adjustment.py",
    "foundation/intelligence/scoring/risk_adjustment.py",
    "tests/intelligence/scoring/test_composite_engine.py",
    "tests/intelligence/scoring/test_adjustments.py",
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
        [sys.executable, "-m", "pytest", "tests/intelligence/scoring", "-q"],
        [sys.executable, "-m", "pytest", "-q"],
    )
    for command in commands:
        print(f"\n> {' '.join(command)}")
        result = subprocess.run(command, cwd=root)
        if result.returncode != 0:
            print("\nPHASE 3.1.3 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.1.3 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

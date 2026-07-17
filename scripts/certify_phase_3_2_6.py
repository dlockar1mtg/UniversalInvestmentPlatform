"""Certify Phase 3.2.6 validation reporting."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/certification_evaluator.py",
    "foundation/intelligence/validation/validation_reporting.py",
    "foundation/intelligence/validation/report_serialization.py",
    "foundation/intelligence/validation/dashboard_dataset.py",
    "foundation/intelligence/validation/phase_3_2_certification.py",
    "tests/intelligence/validation/test_certification_evaluator.py",
    "tests/intelligence/validation/test_validation_reporting.py",
    "tests/intelligence/validation/test_report_serialization.py",
    "tests/intelligence/validation/test_phase_3_2_certification.py",
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
            print("\nPHASE 3.2.6 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.6 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Certify Phase 3.2.3 ranking and calibration metrics."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/ranking_metrics.py",
    "foundation/intelligence/validation/classification_metrics.py",
    "foundation/intelligence/validation/calibration_metrics.py",
    "foundation/intelligence/validation/stability_metrics.py",
    "foundation/intelligence/validation/validation_metrics_engine.py",
    "tests/intelligence/validation/test_ranking_metrics.py",
    "tests/intelligence/validation/test_classification_metrics.py",
    "tests/intelligence/validation/test_calibration_metrics.py",
    "tests/intelligence/validation/test_validation_metrics_engine.py",
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
            print("\nPHASE 3.2.3 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.3 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Certify Phase 3.2.1 historical validation contracts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/__init__.py",
    "foundation/intelligence/validation/historical_observation.py",
    "foundation/intelligence/validation/prediction_record.py",
    "foundation/intelligence/validation/outcome_record.py",
    "foundation/intelligence/validation/backtest_configuration.py",
    "foundation/intelligence/validation/validation_profile.py",
    "foundation/intelligence/validation/validation_result.py",
    "config/intelligence/validation/validation_profiles.yaml",
    "config/intelligence/validation/benchmark_definitions.yaml",
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
            print("\nPHASE 3.2.1 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.1 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

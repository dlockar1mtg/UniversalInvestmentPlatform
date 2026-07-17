"""Certify Phase 3.2.2 walk-forward backtesting engine."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/backtest_schedule.py",
    "foundation/intelligence/validation/point_in_time.py",
    "foundation/intelligence/validation/outcome_alignment.py",
    "foundation/intelligence/validation/backtest_dataset.py",
    "foundation/intelligence/validation/walk_forward_engine.py",
    "tests/intelligence/validation/test_backtest_schedule.py",
    "tests/intelligence/validation/test_point_in_time.py",
    "tests/intelligence/validation/test_outcome_alignment.py",
    "tests/intelligence/validation/test_walk_forward_engine.py",
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
            print("\nPHASE 3.2.2 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.2 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Certify Phase 3.1.2 normalization engine."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/scoring/normalization.py",
    "foundation/intelligence/scoring/normalization_engine.py",
    "foundation/intelligence/scoring/normalization_registry.py",
    "foundation/intelligence/scoring/normalization_strategy.py",
    "foundation/intelligence/scoring/strategies/higher_is_better.py",
    "foundation/intelligence/scoring/strategies/lower_is_better.py",
    "foundation/intelligence/scoring/strategies/target_centered.py",
    "foundation/intelligence/scoring/strategies/percentile.py",
    "foundation/intelligence/scoring/strategies/binary.py",
    "foundation/intelligence/scoring/strategies/categorical.py",
    "foundation/intelligence/scoring/strategies/piecewise.py",
    "config/intelligence/scoring/normalization_profiles.yaml",
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
            print("\nPHASE 3.1.2 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.1.2 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Certify Phase 3.2.4 benchmark comparison engine."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/validation/benchmark_metrics.py",
    "foundation/intelligence/validation/benchmark_registry.py",
    "foundation/intelligence/validation/benchmark_loader.py",
    "foundation/intelligence/validation/benchmark_comparison_engine.py",
    "tests/intelligence/validation/test_benchmark_metrics.py",
    "tests/intelligence/validation/test_benchmark_registry.py",
    "tests/intelligence/validation/test_benchmark_comparison_engine.py",
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
            print("\nPHASE 3.2.4 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2.4 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

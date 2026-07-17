"""Certify Phase 3.1.4 scoring model registry."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/scoring/scoring_model.py",
    "foundation/intelligence/scoring/scoring_model_registry.py",
    "foundation/intelligence/scoring/scoring_model_loader.py",
    "foundation/intelligence/scoring/scoring_model_service.py",
    "config/intelligence/scoring/scoring_model_registry.yaml",
    "tests/intelligence/scoring/test_scoring_model_registry.py",
    "tests/intelligence/scoring/test_scoring_model_loader.py",
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
            print("\nPHASE 3.1.4 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.1.4 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Certify Phase 3.1.5 asset-class scoring profiles."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "foundation/intelligence/scoring/asset_profile.py",
    "foundation/intelligence/scoring/asset_profile_loader.py",
    "foundation/intelligence/scoring/asset_profile_service.py",
    "config/intelligence/scoring/profiles/crypto_v1.yaml",
    "config/intelligence/scoring/profiles/etf_v1.yaml",
    "config/intelligence/scoring/profiles/metals_v1.yaml",
    "config/intelligence/scoring/profiles/mtg_v1.yaml",
    "config/intelligence/scoring/profiles/housing_v1.yaml",
    "config/intelligence/scoring/profiles/cash_v1.yaml",
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
            print("\nPHASE 3.1.5 CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.1.5 CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

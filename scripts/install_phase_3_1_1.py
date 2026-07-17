"""Install Phase 3.1.1 scoring contracts into the repository."""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


def main() -> int:
    source_root = Path(__file__).resolve().parents[1]
    repository_root = Path.cwd()

    required = repository_root / "foundation"
    if not required.exists():
        print("ERROR: Run this installer from the InvestmentPlatform repository root.")
        return 1

    installed = 0
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        if relative.as_posix() == "scripts/install_phase_3_1_1.py":
            continue
        destination = repository_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        installed += 1
        print(f"Installed: {relative}")

    print(f"\nPhase 3.1.1 installation complete. Files installed: {installed}")
    print("Next command: python -m pytest tests/intelligence/scoring -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

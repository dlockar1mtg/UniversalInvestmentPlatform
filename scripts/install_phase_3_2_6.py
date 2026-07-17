"""Install Phase 3.2.6 validation reporting and certification."""

from __future__ import annotations

from pathlib import Path
import shutil


def main() -> int:
    source_root = Path(__file__).resolve().parents[1]
    repository_root = Path.cwd()

    if not (repository_root / "foundation" / "intelligence" / "validation").exists():
        print("ERROR: Run from the InvestmentPlatform root after Phase 3.2.5.")
        return 1

    installed = 0
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        if relative.as_posix() in {
            "scripts/install_phase_3_2_6.py",
            "scripts/certify_phase_3_2_6.py",
            "scripts/certify_phase_3_2_final.py",
        }:
            continue
        destination = repository_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        installed += 1
        print(f"Installed: {relative}")

    print(f"\nPhase 3.2.6 installation complete. Files installed: {installed}")
    print("Next command: python scripts/certify_phase_3_2_6.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

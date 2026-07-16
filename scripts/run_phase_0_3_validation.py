from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name

    print(f"\nRunning {script_name}")
    print("=" * 72)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"{script_name} failed with exit code "
            f"{result.returncode}"
        )


def main() -> None:
    run_script("generate_json_schemas.py")
    run_script("validate_contracts.py")

    print("\nPhase 0.3 contract validation completed successfully.")


if __name__ == "__main__":
    main()
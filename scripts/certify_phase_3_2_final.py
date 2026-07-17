"""Final certification for the complete Phase 3.2 framework."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path.cwd()

    # When a script is executed by path, Python initially places the scripts
    # directory on sys.path rather than the repository root. Add the root before
    # importing the foundation package.
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    from foundation.intelligence.validation import certify_phase_3_2_structure

    structure = certify_phase_3_2_structure(root)
    print(structure.message)
    print(f"Required files checked: {structure.required_files_checked}")
    if not structure.passed:
        for path in structure.missing_files:
            print(f" - Missing: {path}")
        return 1

    commands = (
        [sys.executable, "-m", "pytest", "tests/intelligence/validation", "-q"],
        [sys.executable, "-m", "pytest", "tests/intelligence/scoring", "-q"],
        [sys.executable, "-m", "pytest", "-q"],
    )
    for command in commands:
        print(f"\n> {' '.join(command)}")
        result = subprocess.run(command, cwd=root)
        if result.returncode != 0:
            print("\nPHASE 3.2 FINAL CERTIFICATION FAILED")
            return result.returncode

    print("\nPHASE 3.2 HISTORICAL VALIDATION FRAMEWORK CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

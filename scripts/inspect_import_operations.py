"""Inspect Universal import audit and platform-registry health."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.operations import (
    fetch_platform_health,
    fetch_recent_errors,
    fetch_recent_imports,
)


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    try:
        health = fetch_platform_health(config)
        imports = fetch_recent_imports(config)
        errors = fetch_recent_errors(config)
    except Exception as exc:
        print("UNIVERSAL IMPORT OPERATIONS: FAILED")
        print(str(exc))
        return 1

    print("=" * 72)
    print("Universal Platform Registry Health")
    print("=" * 72)
    print(health.to_string(index=False) if not health.empty else "No platforms registered.")
    print()
    print("=" * 72)
    print("Recent Import Attempts")
    print("=" * 72)
    print(imports.to_string(index=False) if not imports.empty else "No imports recorded.")
    print()
    print("=" * 72)
    print("Recent Import Errors")
    print("=" * 72)
    print(errors.to_string(index=False) if not errors.empty else "No errors recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

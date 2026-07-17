"""Apply Phase 1.3.5 audit and registry database migration."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.audit import (
    apply_audit_registry_migration,
    rebuild_platform_registry,
)
from foundation.import_engine.config import ImportEngineConfig


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    try:
        apply_audit_registry_migration(config)
        rebuild_platform_registry(config)
    except Exception as exc:
        print("PHASE 1.3.5 MIGRATION: FAILED")
        print(str(exc))
        return 1

    print("PHASE 1.3.5 MIGRATION: PASS")
    print(f"Database: {config.database_path}")
    print("Platform registry rebuilt from successful import history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

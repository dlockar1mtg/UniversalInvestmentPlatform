"""Initialize the Universal Investment Intelligence Platform database."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import (
    initialize_database,
    list_database_objects,
)


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    try:
        initialize_database(config)
        objects = list_database_objects(config)
    except Exception as exc:
        print("UNIVERSAL DATABASE INITIALIZATION: FAILED")
        print(str(exc))
        return 1

    table_count = sum(
        1 for _, object_type in objects if object_type == "BASE TABLE"
    )
    view_count = sum(
        1 for _, object_type in objects if object_type == "VIEW"
    )

    print("UNIVERSAL DATABASE INITIALIZATION: PASS")
    print(f"Database: {config.database_path}")
    print(f"Tables: {table_count}")
    print(f"Views: {view_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
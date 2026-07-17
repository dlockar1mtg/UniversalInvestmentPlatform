"""Inspect the Universal Investment Intelligence Platform database."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import (
    get_table_count,
    list_database_objects,
)


def main() -> int:
    config = ImportEngineConfig.from_repository_root(REPOSITORY_ROOT)

    if not config.database_path.is_file():
        print("UNIVERSAL DATABASE INSPECTION: FAILED")
        print(f"Database not found: {config.database_path}")
        return 1

    try:
        objects = list_database_objects(config)
    except Exception as exc:
        print("UNIVERSAL DATABASE INSPECTION: FAILED")
        print(str(exc))
        return 1

    print("=" * 72)
    print("Universal Investment Intelligence Platform Database")
    print("=" * 72)
    print(f"Database: {config.database_path}")
    print()

    for object_name, object_type in objects:
        if object_type == "BASE TABLE":
            row_count = get_table_count(config, object_name)
            print(f"TABLE  {object_name:<40} rows={row_count}")
        else:
            print(f"VIEW   {object_name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
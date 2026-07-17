"""Apply Phase 1.3.6.1 health-status hotfix."""

from __future__ import annotations

from pathlib import Path
import sys

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

SQL_PATH = (
    REPOSITORY_ROOT
    / "foundation"
    / "import_engine"
    / "sql"
    / "003_health_status_latest_attempt.sql"
)


def main() -> int:
    database_path = (
        REPOSITORY_ROOT
        / "data"
        / "universal"
        / "universal_investment.duckdb"
    )

    if not SQL_PATH.is_file():
        print("PHASE 1.3.6.1 HEALTH HOTFIX: FAILED")
        print(f"SQL file not found: {SQL_PATH}")
        return 1

    connection = duckdb.connect(str(database_path))

    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(SQL_PATH.read_text(encoding="utf-8"))
        connection.execute("COMMIT")

        row = connection.execute(
            """
            SELECT registry_status, last_import_status, health_status
            FROM universal_import_health
            WHERE platform_id = 'metals'
            """
        ).fetchone()
    except Exception as exc:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        print("PHASE 1.3.6.1 HEALTH HOTFIX: FAILED")
        print(str(exc))
        return 1
    finally:
        connection.close()

    print("PHASE 1.3.6.1 HEALTH HOTFIX: PASS")
    if row is not None:
        print(f"Registry status: {row[0]}")
        print(f"Last import status: {row[1]}")
        print(f"Health status: {row[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

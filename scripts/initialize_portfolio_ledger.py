"""Initialize Phase 2.2 portfolio ledger tables and views."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"
SQL_FILES = [
    ROOT / "foundation" / "portfolio_engine" / "sql" / "002_portfolio_ledger.sql",
    ROOT / "foundation" / "portfolio_engine" / "sql" / "003_portfolio_ledger_views.sql",
]


def initialize(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        for sql_file in SQL_FILES:
            connection.execute(sql_file.read_text(encoding="utf-8"))

        objects = connection.execute(
            """
            SELECT table_type, table_name
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
              AND (
                    table_name LIKE 'ledger_%'
                    OR table_name LIKE 'v_ledger_%'
                    OR table_name = 'v_active_ledger_entries'
                  )
            ORDER BY table_type, table_name
            """
        ).fetchall()

    print("Universal Portfolio Ledger initialized.")
    print(f"Database: {database_path}")
    print(f"Ledger objects: {len(objects)}")
    for object_type, name in objects:
        print(f"  {object_type}: portfolio.{name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    initialize(args.database.resolve())


if __name__ == "__main__":
    main()

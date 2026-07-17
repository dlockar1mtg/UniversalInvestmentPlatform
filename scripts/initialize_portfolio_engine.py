"""Initialize the Phase 2.1 portfolio database schema."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"
SCHEMA_FILE = ROOT / "foundation" / "portfolio_engine" / "sql" / "001_portfolio_domain.sql"


def initialize(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_FILE.read_text(encoding="utf-8")

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(sql)
        table_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
            """
        ).fetchone()[0]
    finally:
        connection.close()

    print("Universal Portfolio Engine initialized.")
    print(f"Database: {database_path}")
    print(f"Portfolio schema objects: {table_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"DuckDB database path. Default: {DEFAULT_DATABASE}",
    )
    args = parser.parse_args()
    initialize(args.database.resolve())


if __name__ == "__main__":
    main()

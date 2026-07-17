"""Initialize Phase 2.5 contribution and rebalancing objects."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"
SQL_FILES = [
    ROOT / "foundation" / "portfolio_engine" / "sql" / "008_contribution_rebalancing.sql",
    ROOT / "foundation" / "portfolio_engine" / "sql" / "009_contribution_rebalancing_views.sql",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    database = args.database.resolve()

    with duckdb.connect(str(database)) as connection:
        for sql_file in SQL_FILES:
            connection.execute(sql_file.read_text(encoding="utf-8"))
        rows = connection.execute(
            """
            SELECT table_type, table_name
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
              AND (
                    table_name LIKE 'contribution_%'
                    OR table_name LIKE 'v_%contribution%'
                    OR table_name = 'v_blocked_contributions'
                  )
            ORDER BY table_type, table_name
            """
        ).fetchall()

    print("Contribution and Rebalancing Engine initialized.")
    print(f"Database: {database}")
    print(f"Contribution/rebalancing objects: {len(rows)}")
    for kind, name in rows:
        print(f"  {kind}: portfolio.{name}")


if __name__ == "__main__":
    main()

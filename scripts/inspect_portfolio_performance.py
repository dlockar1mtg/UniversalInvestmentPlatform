"""Inspect latest portfolio performance metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    with duckdb.connect(str(args.database.resolve()), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM portfolio.v_portfolio_performance_summary
            ORDER BY period_end DESC
            """
        ).fetchall()
        columns = [
            item[0] for item in connection.description
        ]

    print("Portfolio Performance Summary")
    print("=" * 120)
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))


if __name__ == "__main__":
    main()

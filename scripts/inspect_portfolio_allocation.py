"""Inspect current portfolio allocation and drift."""

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
            SELECT
                category,
                market_value,
                actual_weight,
                target_weight,
                percentage_point_drift,
                dollar_variance,
                allocation_status
            FROM portfolio.v_allocation_drift
            ORDER BY concentration_rank
            """
        ).fetchall()

    print("Current Portfolio Allocation")
    print("=" * 100)
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))


if __name__ == "__main__":
    main()

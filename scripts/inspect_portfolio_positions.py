"""Inspect current calculated positions."""

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
                asset_id, asset_category, quantity, average_unit_cost,
                cost_basis, latest_price, market_value,
                unrealized_gain_loss, realized_gain_loss,
                portfolio_weight, is_stale
            FROM portfolio.v_current_positions
            ORDER BY market_value DESC, asset_id
            """
        ).fetchall()

    print("Current Portfolio Positions")
    print("=" * 100)
    for row in rows:
        print(" | ".join(str(value) for value in row))


if __name__ == "__main__":
    main()

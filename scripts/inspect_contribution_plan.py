"""Inspect the latest contribution plan."""

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
                current_weight,
                target_weight,
                funding_deficit,
                recommended_contribution,
                projected_weight,
                projected_drift,
                remaining_deficit,
                contribution_status,
                constraint_reason
            FROM portfolio.v_contribution_recommendations
            """
        ).fetchall()

    print("Latest Contribution Recommendations")
    print("=" * 120)
    for row in rows:
        print(" | ".join(str(value) for value in row))


if __name__ == "__main__":
    main()

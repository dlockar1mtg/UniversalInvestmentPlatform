"""Inspect Universal Portfolio Ledger counts and recent activity."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    with duckdb.connect(str(args.database.resolve()), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM portfolio.ledger_entries"
        ).fetchone()[0]
        print("Universal Portfolio Ledger Inspection")
        print("=" * 72)
        print(f"Ledger entries: {count}")

        rows = connection.execute(
            """
            SELECT
                effective_at,
                transaction_type,
                asset_id,
                quantity,
                gross_amount,
                fees,
                net_amount,
                source_platform,
                source_record_id
            FROM portfolio.ledger_entries
            ORDER BY effective_at DESC, recorded_at DESC
            LIMIT ?
            """,
            [args.limit],
        ).fetchall()

    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))


if __name__ == "__main__":
    main()

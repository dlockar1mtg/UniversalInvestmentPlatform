"""Import benchmark history CSV into DuckDB."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    with args.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    with duckdb.connect(str(args.database.resolve())) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO portfolio.benchmark_history (
                benchmark_key, benchmark_date, benchmark_value,
                currency, source
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row["benchmark_key"],
                    row["benchmark_date"],
                    row["benchmark_value"],
                    row.get("currency", "USD"),
                    row.get("source"),
                )
                for row in rows
            ],
        )

    print(f"Imported benchmark rows: {len(rows)}")


if __name__ == "__main__":
    main()

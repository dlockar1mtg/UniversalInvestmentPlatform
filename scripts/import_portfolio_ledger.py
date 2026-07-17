"""Import a normalized CSV file into the Universal Portfolio Ledger."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.ledger import (
    LedgerRepository,
    LedgerService,
    normalize_row,
)

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--account-id", type=UUID, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    run_id = uuid4()
    with args.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    entries = [
        normalize_row(
            row,
            portfolio_id=args.portfolio_id,
            account_id=args.account_id,
            import_run_id=run_id,
            source_file=args.csv_file.name,
        )
        for row in rows
    ]

    service = LedgerService(LedgerRepository(args.database.resolve()))
    result = service.post_entries(entries, import_run_id=run_id)

    print("Universal Portfolio Ledger Import")
    print("=" * 72)
    print(f"Import run: {result.import_run_id}")
    print(f"Received: {result.received_count}")
    print(f"Posted: {result.posted_count}")
    print(f"Duplicates: {result.duplicate_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

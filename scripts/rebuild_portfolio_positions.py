"""Rebuild current positions from ledger entries and valuation history."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.ledger import LedgerEntry, LedgerEntryStatus
from foundation.portfolio_engine.models import AssetCategory, TransactionType
from foundation.portfolio_engine.positions import (
    PositionRepository,
    build_positions,
    calculate_cash_balances,
    value_positions,
)
from foundation.portfolio_engine.valuations.valuation_service import resolve_valuations
from foundation.portfolio_engine.valuations import ValuationRepository

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def _load_entries(database: Path, portfolio_id: UUID) -> list[LedgerEntry]:
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                ledger_entry_id, portfolio_id, account_id, transaction_type,
                effective_at, gross_amount, net_amount, currency, recorded_at,
                asset_id, asset_name, asset_category, quantity, unit_price, fees,
                source_platform, source_file, source_record_id, import_run_id,
                reversal_of_entry_id, entry_status, metadata_json
            FROM portfolio.ledger_entries
            WHERE portfolio_id = ?
            ORDER BY effective_at, recorded_at
            """,
            [str(portfolio_id)],
        ).fetchall()

    entries = []
    for row in rows:
        entries.append(
            LedgerEntry(
                ledger_entry_id=row[0],
                portfolio_id=row[1],
                account_id=row[2],
                transaction_type=TransactionType(row[3]),
                effective_at=row[4].replace(tzinfo=timezone.utc),
                gross_amount=row[5],
                net_amount=row[6],
                currency=row[7],
                recorded_at=row[8].replace(tzinfo=timezone.utc),
                asset_id=row[9],
                asset_name=row[10],
                asset_category=AssetCategory(row[11]) if row[11] else None,
                quantity=row[12],
                unit_price=row[13],
                fees=row[14],
                source_platform=row[15],
                source_file=row[16],
                source_record_id=row[17],
                import_run_id=row[18],
                reversal_of_entry_id=row[19],
                entry_status=LedgerEntryStatus(row[20]),
                metadata={} if row[21] is None else dict(row[21]),
            )
        )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--as-of", type=datetime)
    args = parser.parse_args()

    database = args.database.resolve()
    as_of = args.as_of or datetime.now(timezone.utc)
    entries = _load_entries(database, args.portfolio_id)
    derived = build_positions(entries, as_of=as_of)
    valuations = resolve_valuations(
        derived,
        ValuationRepository(database),
        as_of=as_of,
    )
    valued = value_positions(derived, valuations)
    count = PositionRepository(database).replace_portfolio_positions(
        args.portfolio_id,
        valued,
    )

    balances = calculate_cash_balances(entries)
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            "DELETE FROM portfolio.cash_balances WHERE portfolio_id = ?",
            [str(args.portfolio_id)],
        )
        for (account_id, currency), balance in balances.items():
            connection.execute(
                """
                INSERT INTO portfolio.cash_balances
                VALUES (?, ?, ?, ?, ?)
                """,
                [str(args.portfolio_id), str(account_id), currency, balance, as_of],
            )

    print("Portfolio positions rebuilt.")
    print(f"Ledger entries: {len(entries)}")
    print(f"Positions: {count}")
    print(f"Cash balances: {len(balances)}")


if __name__ == "__main__":
    main()

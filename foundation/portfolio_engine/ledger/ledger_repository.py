"""DuckDB repository for the append-only portfolio ledger."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from uuid import UUID

import duckdb

from .ledger_entry import LedgerEntry


class LedgerRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.database_path))

    def existing_hashes(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT audit_hash FROM portfolio.ledger_entries"
            ).fetchall()
        return {row[0] for row in rows}

    def existing_source_keys(self) -> set[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_platform, source_record_id
                FROM portfolio.ledger_entries
                WHERE source_platform IS NOT NULL
                  AND source_record_id IS NOT NULL
                """
            ).fetchall()
        return {(row[0], row[1]) for row in rows}

    def append(self, entry: LedgerEntry) -> None:
        self.append_many([entry])

    def append_many(self, entries: Iterable[LedgerEntry]) -> int:
        rows = list(entries)
        if not rows:
            return 0

        sql = """
        INSERT INTO portfolio.ledger_entries (
            ledger_entry_id, portfolio_id, account_id, asset_id, asset_name,
            asset_category, transaction_type, effective_at, recorded_at,
            quantity, unit_price, gross_amount, fees, net_amount, currency,
            source_platform, source_file, source_record_id, import_run_id,
            reversal_of_entry_id, audit_hash, entry_status, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        parameters = [
            (
                str(entry.ledger_entry_id),
                str(entry.portfolio_id),
                str(entry.account_id),
                entry.asset_id,
                entry.asset_name,
                entry.asset_category.value if entry.asset_category else None,
                entry.transaction_type.value,
                entry.effective_at,
                entry.recorded_at,
                entry.quantity,
                entry.unit_price,
                entry.gross_amount,
                entry.fees,
                entry.net_amount,
                entry.currency,
                entry.source_platform,
                entry.source_file,
                entry.source_record_id,
                str(entry.import_run_id) if entry.import_run_id else None,
                str(entry.reversal_of_entry_id) if entry.reversal_of_entry_id else None,
                entry.audit_hash,
                entry.entry_status.value,
                entry.metadata_json,
            )
            for entry in rows
        ]

        with self._connect() as connection:
            connection.executemany(sql, parameters)
        return len(rows)

    def get(self, ledger_entry_id: UUID) -> tuple | None:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM portfolio.ledger_entries
                WHERE ledger_entry_id = ?
                """,
                [str(ledger_entry_id)],
            ).fetchone()

    def count(self) -> int:
        with self._connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM portfolio.ledger_entries"
            ).fetchone()[0]

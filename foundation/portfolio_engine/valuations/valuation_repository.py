"""DuckDB repository for valuation history."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import duckdb

from foundation.portfolio_engine.models import (
    Valuation,
    ValuationConfidence,
    ValuationSource,
)


class ValuationRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def list_for_asset(
        self,
        asset_id: str,
        *,
        account_id: UUID | None = None,
    ) -> list[Valuation]:
        sql = """
        SELECT
            valuation_id, asset_id, account_id, price, currency, valued_at,
            source, confidence, source_reference, created_at
        FROM portfolio.valuations
        WHERE asset_id = ?
          AND (? IS NULL OR account_id = ? OR account_id IS NULL)
        ORDER BY valued_at
        """
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            rows = connection.execute(
                sql,
                [
                    asset_id,
                    str(account_id) if account_id else None,
                    str(account_id) if account_id else None,
                ],
            ).fetchall()

        return [
            Valuation(
                valuation_id=row[0],
                asset_id=row[1],
                account_id=row[2],
                price=row[3],
                currency=row[4],
                valued_at=row[5],
                source=ValuationSource(row[6]),
                confidence=ValuationConfidence(row[7]),
                source_reference=row[8],
                created_at=row[9],
            )
            for row in rows
        ]

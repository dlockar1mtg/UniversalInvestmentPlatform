"""DuckDB persistence for portfolio snapshots."""

from __future__ import annotations

from pathlib import Path

import duckdb

from foundation.portfolio_engine.models import PortfolioSnapshot


class SnapshotRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def insert(self, snapshot: PortfolioSnapshot) -> None:
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO portfolio.portfolio_snapshots (
                    snapshot_id, portfolio_id, snapshot_at, total_market_value,
                    total_cost_basis, cash_balance, total_unrealized_gain_loss,
                    total_realized_gain_loss, stale_valuation_value, position_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(snapshot.snapshot_id),
                    str(snapshot.portfolio_id),
                    snapshot.snapshot_at,
                    snapshot.total_market_value,
                    snapshot.total_cost_basis,
                    snapshot.cash_balance,
                    snapshot.total_unrealized_gain_loss,
                    snapshot.total_realized_gain_loss,
                    snapshot.stale_valuation_value,
                    snapshot.position_count,
                ],
            )

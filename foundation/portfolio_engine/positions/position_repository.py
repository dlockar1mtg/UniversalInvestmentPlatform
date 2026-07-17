"""DuckDB persistence for calculated positions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from uuid import UUID

import duckdb

from .position_service import ValuedPosition


class PositionRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def replace_portfolio_positions(
        self,
        portfolio_id: UUID,
        positions: Iterable[ValuedPosition],
    ) -> int:
        rows = list(positions)
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                "DELETE FROM portfolio.current_positions WHERE portfolio_id = ?",
                [str(portfolio_id)],
            )
            if rows:
                connection.executemany(
                    """
                    INSERT INTO portfolio.current_positions (
                        position_id, portfolio_id, account_id, asset_id, asset_name,
                        asset_category, quantity, average_unit_cost, cost_basis,
                        latest_price, market_value, unrealized_gain_loss,
                        realized_gain_loss, portfolio_weight, currency,
                        liquidity_tier, valued_at, valuation_source,
                        valuation_confidence, valuation_age_days, is_stale, as_of
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(position.position_id),
                            str(position.portfolio_id),
                            str(position.account_id),
                            position.asset_id,
                            position.asset_name,
                            position.asset_category.value,
                            position.quantity,
                            position.average_unit_cost,
                            position.cost_basis,
                            position.latest_price,
                            position.market_value,
                            position.unrealized_gain_loss,
                            position.realized_gain_loss,
                            position.portfolio_weight,
                            position.currency,
                            position.liquidity_tier.value,
                            position.valued_at,
                            position.valuation_source.value if position.valuation_source else None,
                            position.valuation_confidence.value if position.valuation_confidence else None,
                            position.valuation_age_days,
                            position.is_stale,
                            position.as_of,
                        )
                        for position in rows
                    ],
                )
        return len(rows)

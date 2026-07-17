"""DuckDB persistence for calculated allocations."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import duckdb

from .allocation_calculator import AllocationSummary


class AllocationRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def replace_summary(
        self,
        portfolio_id: UUID,
        summary: AllocationSummary,
    ) -> UUID:
        run_id = uuid4()
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                "DELETE FROM portfolio.current_allocations WHERE portfolio_id = ?",
                [str(portfolio_id)],
            )
            if summary.rows:
                connection.executemany(
                    """
                    INSERT INTO portfolio.current_allocations (
                        allocation_id, calculation_run_id, portfolio_id,
                        allocation_level, allocation_key, market_value,
                        actual_weight, target_weight, minimum_weight,
                        maximum_weight, percentage_point_drift, relative_drift,
                        target_value, dollar_variance, allocation_status,
                        stale_market_value, unvalued_cost_basis,
                        position_count, concentration_rank
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(uuid4()),
                            str(run_id),
                            str(row.portfolio_id),
                            row.level.value,
                            row.allocation_key,
                            row.market_value,
                            row.actual_weight,
                            row.target_weight,
                            row.minimum_weight,
                            row.maximum_weight,
                            row.percentage_point_drift,
                            row.relative_drift,
                            row.target_value,
                            row.dollar_variance,
                            row.status.value,
                            row.stale_market_value,
                            row.unvalued_cost_basis,
                            row.position_count,
                            row.concentration_rank,
                        )
                        for row in summary.rows
                    ],
                )

            connection.execute(
                """
                INSERT INTO portfolio.allocation_calculation_runs (
                    calculation_run_id, portfolio_id, invested_value, cash_value,
                    total_wealth, stale_market_value, unvalued_cost_basis,
                    unvalued_position_count, largest_category_weight,
                    top_three_category_weight, herfindahl_index,
                    effective_category_count, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                [
                    str(run_id),
                    str(portfolio_id),
                    summary.invested_value,
                    summary.cash_value,
                    summary.total_wealth,
                    summary.stale_market_value,
                    summary.unvalued_cost_basis,
                    summary.unvalued_position_count,
                    summary.concentration.largest_weight,
                    summary.concentration.top_three_weight,
                    summary.concentration.herfindahl_index,
                    summary.concentration.effective_holding_count,
                ],
            )
        return run_id

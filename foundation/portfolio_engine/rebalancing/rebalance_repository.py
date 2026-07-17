"""DuckDB persistence for contribution plans."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import duckdb

from .contribution_plan import ContributionPlan


class RebalanceRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def store_plan(
        self,
        portfolio_id: UUID,
        plan: ContributionPlan,
    ) -> UUID:
        plan_id = uuid4()
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO portfolio.contribution_plans (
                    contribution_plan_id, portfolio_id, total_contribution,
                    allocated_contribution, unallocated_cash,
                    current_portfolio_value, projected_portfolio_value, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'generated')
                """,
                [
                    str(plan_id),
                    str(portfolio_id),
                    plan.total_contribution,
                    plan.allocated_contribution,
                    plan.unallocated_cash,
                    plan.current_portfolio_value,
                    plan.projected_portfolio_value,
                ],
            )

            if plan.rows:
                connection.executemany(
                    """
                    INSERT INTO portfolio.contribution_plan_lines (
                        contribution_plan_line_id, contribution_plan_id,
                        portfolio_id, category, current_value, current_weight,
                        target_weight, projected_target_value, funding_deficit,
                        requested_contribution, recommended_contribution,
                        retained_cash, projected_value, projected_weight,
                        projected_drift, remaining_deficit, contribution_status,
                        constraint_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(uuid4()),
                            str(plan_id),
                            str(portfolio_id),
                            row.category.value,
                            row.current_value,
                            row.current_weight,
                            row.target_weight,
                            row.projected_target_value,
                            row.funding_deficit,
                            row.requested_contribution,
                            row.recommended_contribution,
                            row.retained_cash,
                            row.projected_value,
                            row.projected_weight,
                            row.projected_drift,
                            row.remaining_deficit,
                            row.status.value,
                            row.constraint_reason,
                        )
                        for row in plan.rows
                    ],
                )
        return plan_id

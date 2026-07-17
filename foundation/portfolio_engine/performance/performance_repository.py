"""DuckDB persistence for portfolio performance analytics."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import duckdb


class PerformanceRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def store_summary(
        self,
        *,
        portfolio_id: UUID,
        period_start,
        period_end,
        period_return,
        time_weighted_return,
        money_weighted_return,
        annualized_return,
        risk_summary,
        benchmark_key: str | None = None,
        benchmark_return=None,
        excess_return=None,
    ) -> UUID:
        run_id = uuid4()
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO portfolio.performance_runs (
                    performance_run_id, portfolio_id, period_start, period_end,
                    period_return, time_weighted_return, money_weighted_return,
                    annualized_return, annualized_volatility,
                    downside_deviation, maximum_drawdown,
                    drawdown_peak_date, drawdown_trough_date, recovery_date,
                    recovery_days, sharpe_ratio, sortino_ratio, calmar_ratio,
                    positive_period_percentage, best_period_return,
                    worst_period_return, benchmark_key, benchmark_return,
                    excess_return, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                [
                    str(run_id),
                    str(portfolio_id),
                    period_start,
                    period_end,
                    period_return,
                    time_weighted_return,
                    money_weighted_return,
                    annualized_return,
                    risk_summary.annualized_volatility,
                    risk_summary.downside_deviation,
                    risk_summary.maximum_drawdown,
                    risk_summary.drawdown_peak_date,
                    risk_summary.drawdown_trough_date,
                    risk_summary.recovery_date,
                    risk_summary.recovery_days,
                    risk_summary.sharpe_ratio,
                    risk_summary.sortino_ratio,
                    risk_summary.calmar_ratio,
                    risk_summary.positive_period_percentage,
                    risk_summary.best_period_return,
                    risk_summary.worst_period_return,
                    benchmark_key,
                    benchmark_return,
                    excess_return,
                ],
            )
        return run_id

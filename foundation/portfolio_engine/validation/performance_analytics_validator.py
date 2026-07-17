"""Validate Phase 2.6 performance analytics objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


REQUIRED_TABLES = {
    "performance_runs",
    "performance_periods",
    "performance_attribution",
    "benchmark_history",
    "benchmark_returns",
}

REQUIRED_VIEWS = {
    "v_latest_performance_run",
    "v_portfolio_performance_summary",
    "v_performance_attribution",
    "v_performance_risk_flags",
    "v_benchmark_comparison",
}


@dataclass(slots=True)
class PerformanceAnalyticsValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_performance_analytics_database(
    database_path: Path,
) -> PerformanceAnalyticsValidationResult:
    if not database_path.exists():
        return PerformanceAnalyticsValidationResult(
            errors=[f"Database not found: {database_path}"],
            warnings=[],
        )

    errors: list[str] = []
    warnings: list[str] = []

    with duckdb.connect(str(database_path), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
            """
        ).fetchall()
        tables = {name for name, kind in rows if kind == "BASE TABLE"}
        views = {name for name, kind in rows if kind == "VIEW"}

        missing_tables = sorted(REQUIRED_TABLES - tables)
        missing_views = sorted(REQUIRED_VIEWS - views)
        if missing_tables:
            errors.append(f"Missing tables: {', '.join(missing_tables)}")
        if missing_views:
            errors.append(f"Missing views: {', '.join(missing_views)}")

        if "performance_runs" in tables:
            invalid = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.performance_runs
                WHERE period_end < period_start
                   OR positive_period_percentage < 0
                   OR positive_period_percentage > 1
                """
            ).fetchone()[0]
            if invalid:
                errors.append(f"Found {invalid} invalid performance runs.")

    return PerformanceAnalyticsValidationResult(errors=errors, warnings=warnings)

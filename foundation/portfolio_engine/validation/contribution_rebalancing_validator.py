"""Validate Phase 2.5 database objects and contribution plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


REQUIRED_TABLES = {
    "contribution_plans",
    "contribution_plan_lines",
}

REQUIRED_VIEWS = {
    "v_latest_contribution_plan",
    "v_latest_contribution_plan_lines",
    "v_contribution_recommendations",
    "v_contribution_plan_summary",
    "v_blocked_contributions",
}


@dataclass(slots=True)
class ContributionRebalancingValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_contribution_rebalancing_database(
    database_path: Path,
) -> ContributionRebalancingValidationResult:
    if not database_path.exists():
        return ContributionRebalancingValidationResult(
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

        if "contribution_plans" in tables:
            invalid_plans = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.contribution_plans
                WHERE total_contribution < 0
                   OR allocated_contribution < 0
                   OR unallocated_cash < 0
                   OR ABS(
                        allocated_contribution
                        + unallocated_cash
                        - total_contribution
                   ) > 0.01
                """
            ).fetchone()[0]
            if invalid_plans:
                errors.append(f"Found {invalid_plans} invalid contribution plans.")

        if "contribution_plan_lines" in tables:
            invalid_lines = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.contribution_plan_lines
                WHERE recommended_contribution < 0
                   OR retained_cash < 0
                   OR projected_weight < 0
                   OR projected_weight > 1
                """
            ).fetchone()[0]
            if invalid_lines:
                errors.append(f"Found {invalid_lines} invalid contribution lines.")

    return ContributionRebalancingValidationResult(
        errors=errors,
        warnings=warnings,
    )

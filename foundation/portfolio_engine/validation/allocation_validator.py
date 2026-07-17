"""Validate Phase 2.4 allocation database objects and results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


REQUIRED_TABLES = {
    "current_allocations",
    "allocation_calculation_runs",
}

REQUIRED_VIEWS = {
    "v_category_allocation",
    "v_allocation_drift",
    "v_underweight_categories",
    "v_overweight_categories",
    "v_allocation_data_quality",
    "v_latest_allocation_run",
}


@dataclass(slots=True)
class AllocationValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_allocation_database(database_path: Path) -> AllocationValidationResult:
    if not database_path.exists():
        return AllocationValidationResult(
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

        if "current_allocations" in tables:
            invalid = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.current_allocations
                WHERE market_value < 0
                   OR actual_weight < 0
                   OR actual_weight > 1
                   OR position_count < 0
                """
            ).fetchone()[0]
            if invalid:
                errors.append(f"Found {invalid} invalid allocation rows.")

            category_total = connection.execute(
                """
                SELECT COALESCE(MAX(total_weight), 0)
                FROM (
                    SELECT portfolio_id, SUM(actual_weight) AS total_weight
                    FROM portfolio.current_allocations
                    WHERE allocation_level = 'category'
                      AND allocation_key <> 'cash'
                    GROUP BY portfolio_id
                )
                """
            ).fetchone()[0]
            if category_total and abs(category_total - 1) > 0.000001:
                warnings.append(
                    f"Category allocation weights total {category_total}, not 1.0."
                )

    return AllocationValidationResult(errors=errors, warnings=warnings)

"""Validate Phase 2.3 database objects and calculated positions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


REQUIRED_TABLES = {
    "current_positions",
    "position_rebuild_runs",
    "cash_balances",
}

REQUIRED_VIEWS = {
    "v_current_positions",
    "v_portfolio_position_summary",
    "v_unvalued_positions",
    "v_stale_positions",
    "v_portfolio_total_value",
}


@dataclass(slots=True)
class PositionValuationValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_position_valuation_database(
    database_path: Path,
) -> PositionValuationValidationResult:
    if not database_path.exists():
        return PositionValuationValidationResult(
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

        if "current_positions" in tables:
            invalid = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.current_positions
                WHERE quantity < 0
                   OR cost_basis < 0
                   OR market_value < 0
                   OR portfolio_weight < 0
                   OR portfolio_weight > 1
                """
            ).fetchone()[0]
            if invalid:
                errors.append(f"Found {invalid} invalid calculated positions.")

            unvalued = connection.execute(
                "SELECT COUNT(*) FROM portfolio.v_unvalued_positions"
            ).fetchone()[0]
            if unvalued:
                warnings.append(f"{unvalued} position(s) do not have a usable valuation.")

    return PositionValuationValidationResult(errors=errors, warnings=warnings)

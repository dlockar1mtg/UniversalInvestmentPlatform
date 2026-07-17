"""Validation of the initialized Universal Portfolio Ledger."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


REQUIRED_TABLES = {
    "ledger_entries",
    "ledger_import_batches",
    "ledger_rejections",
    "ledger_reconciliation_results",
}

REQUIRED_VIEWS = {
    "v_active_ledger_entries",
    "v_ledger_account_balances",
    "v_ledger_asset_activity",
    "v_ledger_audit_summary",
    "v_ledger_reversals",
}


@dataclass(slots=True)
class LedgerValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_ledger_database(database_path: Path) -> LedgerValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not database_path.exists():
        return LedgerValidationResult(
            errors=[f"Database not found: {database_path}"],
            warnings=[],
        )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        table_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
              AND table_type = 'BASE TABLE'
            """
        ).fetchall()
        view_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'portfolio'
              AND table_type = 'VIEW'
            """
        ).fetchall()

        tables = {row[0] for row in table_rows}
        views = {row[0] for row in view_rows}

        missing_tables = sorted(REQUIRED_TABLES - tables)
        missing_views = sorted(REQUIRED_VIEWS - views)

        if missing_tables:
            errors.append(f"Missing ledger tables: {', '.join(missing_tables)}")
        if missing_views:
            errors.append(f"Missing ledger views: {', '.join(missing_views)}")

        if "ledger_entries" in tables:
            duplicate_hashes = connection.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT audit_hash
                    FROM portfolio.ledger_entries
                    GROUP BY audit_hash
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
            if duplicate_hashes:
                errors.append(f"Found {duplicate_hashes} duplicate audit hashes.")

            invalid_rows = connection.execute(
                """
                SELECT COUNT(*)
                FROM portfolio.ledger_entries
                WHERE audit_hash IS NULL
                   OR length(audit_hash) <> 64
                   OR length(currency) <> 3
                """
            ).fetchone()[0]
            if invalid_rows:
                errors.append(f"Found {invalid_rows} structurally invalid ledger rows.")

    return LedgerValidationResult(errors=errors, warnings=warnings)

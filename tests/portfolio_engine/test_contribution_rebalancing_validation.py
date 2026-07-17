from pathlib import Path

import duckdb

from foundation.portfolio_engine.validation import (
    validate_contribution_rebalancing_database,
)


ROOT = Path(__file__).resolve().parents[2]


def test_initialized_contribution_database_is_valid(tmp_path: Path) -> None:
    database = tmp_path / "rebalance.duckdb"
    with duckdb.connect(str(database)) as connection:
        for name in [
            "001_portfolio_domain.sql",
            "002_portfolio_ledger.sql",
            "003_portfolio_ledger_views.sql",
            "004_position_valuation_engine.sql",
            "005_position_valuation_views.sql",
            "006_allocation_engine.sql",
            "007_allocation_views.sql",
            "008_contribution_rebalancing.sql",
            "009_contribution_rebalancing_views.sql",
        ]:
            connection.execute(
                (ROOT / "foundation/portfolio_engine/sql" / name).read_text()
            )

    result = validate_contribution_rebalancing_database(database)
    assert result.errors == []
    assert result.is_valid

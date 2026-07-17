from pathlib import Path

import duckdb

from foundation.portfolio_engine.validation import (
    validate_position_valuation_database,
)


ROOT = Path(__file__).resolve().parents[2]


def test_initialized_position_valuation_database_is_valid(tmp_path: Path) -> None:
    database = tmp_path / "positions.duckdb"
    sql_files = [
        "001_portfolio_domain.sql",
        "002_portfolio_ledger.sql",
        "003_portfolio_ledger_views.sql",
        "004_position_valuation_engine.sql",
        "005_position_valuation_views.sql",
    ]
    with duckdb.connect(str(database)) as connection:
        for name in sql_files:
            connection.execute(
                (ROOT / "foundation/portfolio_engine/sql" / name).read_text()
            )

    result = validate_position_valuation_database(database)
    assert result.errors == []
    assert result.is_valid

from pathlib import Path

import duckdb

from foundation.portfolio_engine.validation.ledger_validator import (
    validate_ledger_database,
)


ROOT = Path(__file__).resolve().parents[2]


def test_initialized_ledger_is_valid(tmp_path: Path) -> None:
    database = tmp_path / "ledger.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            (ROOT / "foundation/portfolio_engine/sql/001_portfolio_domain.sql").read_text()
        )
        connection.execute(
            (ROOT / "foundation/portfolio_engine/sql/002_portfolio_ledger.sql").read_text()
        )
        connection.execute(
            (ROOT / "foundation/portfolio_engine/sql/003_portfolio_ledger_views.sql").read_text()
        )

    result = validate_ledger_database(database)
    assert result.errors == []
    assert result.is_valid

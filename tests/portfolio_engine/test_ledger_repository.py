from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import duckdb

from foundation.portfolio_engine.ledger import (
    LedgerEntry,
    LedgerRepository,
    LedgerService,
)
from foundation.portfolio_engine.models import TransactionType


ROOT = Path(__file__).resolve().parents[2]


def _initialize(database: Path) -> None:
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


def test_repository_posts_idempotently(tmp_path: Path) -> None:
    database = tmp_path / "ledger.duckdb"
    _initialize(database)
    entry = LedgerEntry(
        portfolio_id=uuid4(),
        account_id=uuid4(),
        transaction_type=TransactionType.DEPOSIT,
        effective_at=datetime.now(timezone.utc),
        gross_amount=Decimal("1000"),
        fees=Decimal("0"),
        net_amount=Decimal("1000"),
        source_platform="test",
        source_record_id="deposit-1",
    )
    service = LedgerService(LedgerRepository(database))
    first = service.post_entries([entry])
    second = service.post_entries([entry])

    assert first.posted_count == 1
    assert second.posted_count == 0
    assert second.duplicate_count == 1
    assert LedgerRepository(database).count() == 1

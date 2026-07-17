from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import duckdb

from foundation.portfolio_engine.allocation import AllocationRepository, AllocationService
from foundation.portfolio_engine.models import AssetCategory, LiquidityTier
from foundation.portfolio_engine.positions import ValuedPosition


ROOT = Path(__file__).resolve().parents[2]


def test_allocation_service_persists_rows(tmp_path: Path) -> None:
    database = tmp_path / "allocation.duckdb"
    with duckdb.connect(str(database)) as connection:
        for name in [
            "001_portfolio_domain.sql",
            "002_portfolio_ledger.sql",
            "003_portfolio_ledger_views.sql",
            "004_position_valuation_engine.sql",
            "005_position_valuation_views.sql",
            "006_allocation_engine.sql",
            "007_allocation_views.sql",
        ]:
            connection.execute(
                (ROOT / "foundation/portfolio_engine/sql" / name).read_text()
            )

    portfolio_id = uuid4()
    position = ValuedPosition(
        portfolio_id=portfolio_id,
        account_id=uuid4(),
        asset_id="BTC",
        asset_name="Bitcoin",
        asset_category=AssetCategory.CRYPTO,
        quantity=Decimal("1"),
        average_unit_cost=Decimal("100"),
        cost_basis=Decimal("100"),
        latest_price=Decimal("100"),
        market_value=Decimal("100"),
        unrealized_gain_loss=Decimal("0"),
        realized_gain_loss=Decimal("0"),
        portfolio_weight=Decimal("1"),
        currency="USD",
        liquidity_tier=LiquidityTier.DAILY,
        valued_at=datetime.now(timezone.utc),
        valuation_source=None,
        valuation_confidence=None,
        valuation_age_days=0,
        is_stale=False,
        as_of=datetime.now(timezone.utc),
    )
    service = AllocationService(
        AllocationRepository(database),
        ROOT / "config/portfolios/allocation_targets.yaml",
    )
    service.calculate_and_store(portfolio_id, [position])

    with duckdb.connect(str(database), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM portfolio.current_allocations"
        ).fetchone()[0]
    assert count == 5

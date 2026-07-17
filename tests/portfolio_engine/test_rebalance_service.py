from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import duckdb

from foundation.portfolio_engine.allocation import (
    AllocationLevel,
    AllocationRow,
    AllocationStatus,
)
from foundation.portfolio_engine.rebalancing import (
    RebalanceRepository,
    RebalanceService,
)


ROOT = Path(__file__).resolve().parents[2]


def test_rebalance_service_persists_plan(tmp_path: Path) -> None:
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

    portfolio_id = uuid4()
    categories = {
        "crypto": "33000",
        "mtg": "20000",
        "metals": "10000",
        "acorns": "10000",
        "stocks_etfs": "27000",
    }
    rows = [
        AllocationRow(
            portfolio_id=portfolio_id,
            level=AllocationLevel.CATEGORY,
            allocation_key=category,
            market_value=Decimal(value),
            actual_weight=Decimal(value) / Decimal("100000"),
            target_weight=None,
            minimum_weight=None,
            maximum_weight=None,
            percentage_point_drift=None,
            relative_drift=None,
            target_value=None,
            dollar_variance=None,
            status=AllocationStatus.WITHIN_BAND,
            stale_market_value=Decimal("0"),
            unvalued_cost_basis=Decimal("0"),
            position_count=1,
        )
        for category, value in categories.items()
    ]
    service = RebalanceService(
        RebalanceRepository(database),
        ROOT / "config/portfolios/allocation_targets.yaml",
        ROOT / "config/portfolios/rebalance_policy.yaml",
    )
    service.generate_and_store(
        portfolio_id,
        rows,
        total_contribution=Decimal("3000"),
    )

    with duckdb.connect(str(database), read_only=True) as connection:
        plan_count = connection.execute(
            "SELECT COUNT(*) FROM portfolio.contribution_plans"
        ).fetchone()[0]
        line_count = connection.execute(
            "SELECT COUNT(*) FROM portfolio.contribution_plan_lines"
        ).fetchone()[0]
    assert plan_count == 1
    assert line_count == 5

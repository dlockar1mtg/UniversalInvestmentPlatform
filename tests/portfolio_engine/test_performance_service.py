from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import duckdb

from foundation.portfolio_engine.performance import (
    DatedCashFlow,
    PerformanceRepository,
    PerformanceService,
)
from foundation.portfolio_engine.risk import ValuePoint


ROOT = Path(__file__).resolve().parents[2]


def test_performance_service_persists_summary(tmp_path: Path) -> None:
    database = tmp_path / "performance.duckdb"
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
            "010_performance_analytics.sql",
            "011_performance_analytics_views.sql",
        ]:
            connection.execute(
                (ROOT / "foundation/portfolio_engine/sql" / name).read_text()
            )

    portfolio_id = uuid4()
    service = PerformanceService(PerformanceRepository(database))
    service.calculate_and_store(
        portfolio_id=portfolio_id,
        period_returns=[Decimal("0.02"), Decimal("0.03")],
        value_points=[
            ValuePoint(date(2026, 1, 31), Decimal("1000")),
            ValuePoint(date(2026, 2, 28), Decimal("1050")),
        ],
        cash_flows=[
            DatedCashFlow(date(2025, 1, 1), Decimal("-1000")),
            DatedCashFlow(date(2026, 1, 1), Decimal("1100")),
        ],
    )

    with duckdb.connect(str(database), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM portfolio.performance_runs"
        ).fetchone()[0]
    assert count == 1

"""Calculate and persist current portfolio allocation."""

from __future__ import annotations

import argparse
import sys
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.allocation import (
    AllocationRepository,
    AllocationService,
)
from foundation.portfolio_engine.models import (
    AssetCategory,
    LiquidityTier,
    ValuationConfidence,
    ValuationSource,
)
from foundation.portfolio_engine.positions import ValuedPosition

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"
DEFAULT_TARGETS = ROOT / "config" / "portfolios" / "allocation_targets.yaml"


def _load_positions(database: Path, portfolio_id: UUID) -> list[ValuedPosition]:
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                position_id, portfolio_id, account_id, asset_id, asset_name,
                asset_category, quantity, average_unit_cost, cost_basis,
                latest_price, market_value, unrealized_gain_loss,
                realized_gain_loss, portfolio_weight, currency,
                liquidity_tier, valued_at, valuation_source,
                valuation_confidence, valuation_age_days, is_stale, as_of
            FROM portfolio.current_positions
            WHERE portfolio_id = ?
            """,
            [str(portfolio_id)],
        ).fetchall()

    return [
        ValuedPosition(
            position_id=row[0],
            portfolio_id=row[1],
            account_id=row[2],
            asset_id=row[3],
            asset_name=row[4],
            asset_category=AssetCategory(row[5]),
            quantity=row[6],
            average_unit_cost=row[7],
            cost_basis=row[8],
            latest_price=row[9],
            market_value=row[10],
            unrealized_gain_loss=row[11],
            realized_gain_loss=row[12],
            portfolio_weight=row[13],
            currency=row[14],
            liquidity_tier=LiquidityTier(row[15]),
            valued_at=row[16].replace(tzinfo=timezone.utc) if row[16] else None,
            valuation_source=ValuationSource(row[17]) if row[17] else None,
            valuation_confidence=ValuationConfidence(row[18]) if row[18] else None,
            valuation_age_days=row[19],
            is_stale=row[20],
            as_of=row[21].replace(tzinfo=timezone.utc),
        )
        for row in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--include-cash", action="store_true")
    args = parser.parse_args()

    database = args.database.resolve()
    positions = _load_positions(database, args.portfolio_id)

    with duckdb.connect(str(database), read_only=True) as connection:
        cash = connection.execute(
            """
            SELECT COALESCE(SUM(cash_balance), 0)
            FROM portfolio.cash_balances
            WHERE portfolio_id = ?
            """,
            [str(args.portfolio_id)],
        ).fetchone()[0]

    service = AllocationService(
        AllocationRepository(database),
        args.targets.resolve(),
    )
    run_id, summary = service.calculate_and_store(
        args.portfolio_id,
        positions,
        cash_value=Decimal(str(cash)),
        include_cash_in_denominator=args.include_cash,
    )

    print("Portfolio allocation calculated.")
    print(f"Calculation run: {run_id}")
    print(f"Positions: {len(positions)}")
    print(f"Invested value: {summary.invested_value}")
    print(f"Cash value: {summary.cash_value}")
    print(f"Total wealth: {summary.total_wealth}")
    print(f"Category rows: {len(summary.rows)}")


if __name__ == "__main__":
    main()

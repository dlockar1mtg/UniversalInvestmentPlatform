"""Create and persist a portfolio snapshot from current positions."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import duckdb

from foundation.portfolio_engine.models import (
    AssetCategory,
    LiquidityTier,
    ValuationConfidence,
    ValuationSource,
)
from foundation.portfolio_engine.positions import ValuedPosition
from foundation.portfolio_engine.snapshots import SnapshotRepository, build_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    database = args.database.resolve()

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
            [str(args.portfolio_id)],
        ).fetchall()
        cash = connection.execute(
            """
            SELECT COALESCE(SUM(cash_balance), 0)
            FROM portfolio.cash_balances
            WHERE portfolio_id = ?
            """,
            [str(args.portfolio_id)],
        ).fetchone()[0]

    positions = [
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
            valued_at=row[16],
            valuation_source=ValuationSource(row[17]) if row[17] else None,
            valuation_confidence=ValuationConfidence(row[18]) if row[18] else None,
            valuation_age_days=row[19],
            is_stale=row[20],
            as_of=row[21],
        )
        for row in rows
    ]
    snapshot = build_snapshot(
        args.portfolio_id,
        positions,
        cash_balance=Decimal(str(cash)),
        snapshot_at=datetime.now(timezone.utc),
    )
    SnapshotRepository(database).insert(snapshot)
    print("Portfolio snapshot created.")
    print(f"Snapshot ID: {snapshot.snapshot_id}")
    print(f"Total market value: {snapshot.total_market_value}")


if __name__ == "__main__":
    main()

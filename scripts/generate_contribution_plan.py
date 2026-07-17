"""Generate and persist a contribution-only rebalancing plan."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.allocation import (
    AllocationLevel,
    AllocationRow,
    AllocationStatus,
)
from foundation.portfolio_engine.rebalancing import (
    RebalanceRepository,
    RebalanceService,
)

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"
DEFAULT_TARGETS = ROOT / "config" / "portfolios" / "allocation_targets.yaml"
DEFAULT_POLICY = ROOT / "config" / "portfolios" / "rebalance_policy.yaml"


def _load_allocation_rows(database: Path, portfolio_id: UUID) -> list[AllocationRow]:
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                portfolio_id, allocation_level, allocation_key, market_value,
                actual_weight, target_weight, minimum_weight, maximum_weight,
                percentage_point_drift, relative_drift, target_value,
                dollar_variance, allocation_status, stale_market_value,
                unvalued_cost_basis, position_count, concentration_rank
            FROM portfolio.current_allocations
            WHERE portfolio_id = ?
              AND allocation_level = 'category'
            """,
            [str(portfolio_id)],
        ).fetchall()

    return [
        AllocationRow(
            portfolio_id=row[0],
            level=AllocationLevel(row[1]),
            allocation_key=row[2],
            market_value=row[3],
            actual_weight=row[4],
            target_weight=row[5],
            minimum_weight=row[6],
            maximum_weight=row[7],
            percentage_point_drift=row[8],
            relative_drift=row[9],
            target_value=row[10],
            dollar_variance=row[11],
            status=AllocationStatus(row[12]),
            stale_market_value=row[13],
            unvalued_cost_basis=row[14],
            position_count=row[15],
            concentration_rank=row[16],
        )
        for row in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--contribution", type=Decimal, default=Decimal("3000"))
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()

    database = args.database.resolve()
    rows = _load_allocation_rows(database, args.portfolio_id)
    if not rows:
        raise SystemExit(
            "No current category allocation rows found. "
            "Run calculate_portfolio_allocation.py first."
        )

    service = RebalanceService(
        RebalanceRepository(database),
        args.targets.resolve(),
        args.policy.resolve(),
    )
    plan_id, plan = service.generate_and_store(
        args.portfolio_id,
        rows,
        total_contribution=args.contribution,
    )

    print("Contribution plan generated.")
    print(f"Plan ID: {plan_id}")
    print(f"Contribution: {plan.total_contribution}")
    print(f"Allocated: {plan.allocated_contribution}")
    print(f"Unallocated cash: {plan.unallocated_cash}")
    print(f"Projected portfolio value: {plan.projected_portfolio_value}")


if __name__ == "__main__":
    main()

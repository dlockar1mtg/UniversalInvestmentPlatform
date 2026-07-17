"""Calculate portfolio performance from a normalized CSV fixture."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.portfolio_engine.performance import (
    DatedCashFlow,
    PerformanceRepository,
    PerformanceService,
)
from foundation.portfolio_engine.risk import ValuePoint

DEFAULT_DATABASE = ROOT / "data" / "integration" / "universal_investment.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--returns-file", type=Path, required=True)
    parser.add_argument("--cash-flows-file", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    with args.returns_file.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    returns = [Decimal(row["period_return"]) for row in rows]
    values = [
        ValuePoint(
            date_value=date.fromisoformat(row["period_end"]),
            value=Decimal(row["ending_value"]),
        )
        for row in rows
    ]

    with args.cash_flows_file.open("r", encoding="utf-8-sig", newline="") as handle:
        flow_rows = list(csv.DictReader(handle))
    flows = [
        DatedCashFlow(
            date_value=date.fromisoformat(row["cash_flow_date"]),
            amount=Decimal(row["amount"]),
        )
        for row in flow_rows
    ]

    service = PerformanceService(
        PerformanceRepository(args.database.resolve())
    )
    run_id, summary = service.calculate_and_store(
        portfolio_id=args.portfolio_id,
        period_returns=returns,
        value_points=values,
        cash_flows=flows,
    )

    print("Portfolio performance calculated.")
    print(f"Run ID: {run_id}")
    print(f"TWR: {summary.time_weighted_return}")
    print(f"MWR: {summary.money_weighted_return}")
    print(f"Annualized return: {summary.annualized_return}")
    print(f"Maximum drawdown: {summary.risk_summary.maximum_drawdown}")
    print(f"Sharpe ratio: {summary.risk_summary.sharpe_ratio}")


if __name__ == "__main__":
    main()

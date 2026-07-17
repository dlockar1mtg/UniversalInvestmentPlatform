"""Load contribution and rebalancing policy from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml


@dataclass(slots=True)
class RebalancePolicy:
    method: str
    evaluation_frequency: str
    absolute_drift_trigger: Decimal
    relative_drift_trigger: Decimal
    permit_sales: bool
    respect_allocation_bands: bool
    respect_minimum_purchase_amounts: bool
    respect_fractional_purchase_rules: bool
    prioritize_most_underweight: bool
    retain_unallocated_cash: bool


def load_rebalance_policy(path: Path) -> RebalancePolicy:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    row = payload.get("rebalance_policy", {})

    policy = RebalancePolicy(
        method=str(row.get("method", "contribution_only")),
        evaluation_frequency=str(row.get("evaluation_frequency", "monthly")),
        absolute_drift_trigger=Decimal(str(row.get("absolute_drift_trigger", 0))),
        relative_drift_trigger=Decimal(str(row.get("relative_drift_trigger", 0))),
        permit_sales=bool(row.get("permit_sales", False)),
        respect_allocation_bands=bool(row.get("respect_allocation_bands", True)),
        respect_minimum_purchase_amounts=bool(
            row.get("respect_minimum_purchase_amounts", True)
        ),
        respect_fractional_purchase_rules=bool(
            row.get("respect_fractional_purchase_rules", True)
        ),
        prioritize_most_underweight=bool(
            row.get("prioritize_most_underweight", True)
        ),
        retain_unallocated_cash=bool(row.get("retain_unallocated_cash", True)),
    )

    if policy.method != "contribution_only":
        raise ValueError("Phase 2.5 supports contribution_only rebalancing.")
    if policy.permit_sales:
        raise ValueError("Phase 2.5 does not permit sales.")
    return policy

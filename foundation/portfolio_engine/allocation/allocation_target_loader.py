"""Load allocation targets from YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from foundation.portfolio_engine.models import AssetCategory


@dataclass(slots=True)
class AllocationTargetConfig:
    category: AssetCategory
    target_weight: Decimal
    minimum_weight: Decimal
    maximum_weight: Decimal
    priority: int
    minimum_purchase_amount: Decimal
    allow_fractional: bool


def load_allocation_targets(path: Path) -> list[AllocationTargetConfig]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = payload.get("allocation_targets", [])
    targets: list[AllocationTargetConfig] = []

    for row in rows:
        targets.append(
            AllocationTargetConfig(
                category=AssetCategory(str(row["category"])),
                target_weight=Decimal(str(row["target_weight"])),
                minimum_weight=Decimal(str(row["minimum_weight"])),
                maximum_weight=Decimal(str(row["maximum_weight"])),
                priority=int(row.get("priority", 100)),
                minimum_purchase_amount=Decimal(
                    str(row.get("minimum_purchase_amount", 0))
                ),
                allow_fractional=bool(row.get("allow_fractional", True)),
            )
        )

    total = sum((target.target_weight for target in targets), Decimal("0"))
    if total != Decimal("1.00") and total != Decimal("1"):
        raise ValueError(f"Allocation targets must total 1.0; found {total}.")

    categories = [target.category for target in targets]
    if len(categories) != len(set(categories)):
        raise ValueError("Allocation targets contain duplicate categories.")

    return targets

"""Calculate category, asset, account, and liquidity allocations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from foundation.portfolio_engine.models import AssetCategory
from foundation.portfolio_engine.positions import ValuedPosition

from .allocation_target_loader import AllocationTargetConfig
from .concentration import ConcentrationResult, calculate_concentration
from .drift_calculator import AllocationStatus, calculate_drift


class AllocationLevel(StrEnum):
    CATEGORY = "category"
    ASSET = "asset"
    ACCOUNT = "account"
    LIQUIDITY = "liquidity"


@dataclass(slots=True)
class AllocationRow:
    portfolio_id: UUID
    level: AllocationLevel
    allocation_key: str
    market_value: Decimal
    actual_weight: Decimal
    target_weight: Decimal | None
    minimum_weight: Decimal | None
    maximum_weight: Decimal | None
    percentage_point_drift: Decimal | None
    relative_drift: Decimal | None
    target_value: Decimal | None
    dollar_variance: Decimal | None
    status: AllocationStatus
    stale_market_value: Decimal
    unvalued_cost_basis: Decimal
    position_count: int
    concentration_rank: int | None = None


@dataclass(slots=True)
class AllocationSummary:
    rows: list[AllocationRow]
    invested_value: Decimal
    cash_value: Decimal
    total_wealth: Decimal
    stale_market_value: Decimal
    unvalued_cost_basis: Decimal
    unvalued_position_count: int
    concentration: ConcentrationResult


def calculate_allocation(
    positions: list[ValuedPosition],
    targets: list[AllocationTargetConfig],
    *,
    cash_value: Decimal = Decimal("0"),
    include_cash_in_denominator: bool = False,
) -> AllocationSummary:
    cash_value = Decimal(str(cash_value))
    target_map = {target.category: target for target in targets}

    included_positions = [
        position
        for position in positions
        if include_cash_in_denominator or position.asset_category != AssetCategory.CASH
    ]
    invested_value = sum(
        (position.market_value for position in included_positions),
        Decimal("0"),
    )
    denominator = invested_value + (cash_value if include_cash_in_denominator else 0)
    total_wealth = invested_value + cash_value

    grouped: dict[AssetCategory, list[ValuedPosition]] = defaultdict(list)
    for position in positions:
        grouped[position.asset_category].append(position)

    rows: list[AllocationRow] = []
    all_categories = set(grouped) | set(target_map)

    for category in sorted(all_categories, key=lambda item: item.value):
        category_positions = grouped.get(category, [])
        market_value = sum(
            (position.market_value for position in category_positions),
            Decimal("0"),
        )
        stale_value = sum(
            (
                position.market_value
                for position in category_positions
                if position.is_stale
            ),
            Decimal("0"),
        )
        unvalued_basis = sum(
            (
                position.cost_basis
                for position in category_positions
                if position.valued_at is None or position.latest_price == 0
            ),
            Decimal("0"),
        )

        target = target_map.get(category)
        if target is None:
            actual_weight = (
                Decimal("0") if denominator == 0 else market_value / denominator
            )
            status = (
                AllocationStatus.NO_VALUE
                if market_value == 0
                else AllocationStatus.UNCONFIGURED
            )
            row = AllocationRow(
                portfolio_id=category_positions[0].portfolio_id
                if category_positions
                else positions[0].portfolio_id,
                level=AllocationLevel.CATEGORY,
                allocation_key=category.value,
                market_value=market_value,
                actual_weight=actual_weight,
                target_weight=None,
                minimum_weight=None,
                maximum_weight=None,
                percentage_point_drift=None,
                relative_drift=None,
                target_value=None,
                dollar_variance=None,
                status=status,
                stale_market_value=stale_value,
                unvalued_cost_basis=unvalued_basis,
                position_count=len(category_positions),
            )
        else:
            drift = calculate_drift(
                actual_value=market_value,
                total_value=denominator,
                target_weight=target.target_weight,
                minimum_weight=target.minimum_weight,
                maximum_weight=target.maximum_weight,
            )
            row = AllocationRow(
                portfolio_id=category_positions[0].portfolio_id
                if category_positions
                else positions[0].portfolio_id,
                level=AllocationLevel.CATEGORY,
                allocation_key=category.value,
                market_value=market_value,
                actual_weight=drift.actual_weight,
                target_weight=drift.target_weight,
                minimum_weight=drift.minimum_weight,
                maximum_weight=drift.maximum_weight,
                percentage_point_drift=drift.percentage_point_drift,
                relative_drift=drift.relative_drift,
                target_value=drift.target_value,
                dollar_variance=drift.dollar_variance,
                status=drift.status,
                stale_market_value=stale_value,
                unvalued_cost_basis=unvalued_basis,
                position_count=len(category_positions),
            )
        rows.append(row)

    ranked = sorted(rows, key=lambda row: row.market_value, reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row.concentration_rank = rank

    stale_market_value = sum(
        (position.market_value for position in positions if position.is_stale),
        Decimal("0"),
    )
    unvalued_positions = [
        position
        for position in positions
        if position.valued_at is None or position.latest_price == 0
    ]
    concentration = calculate_concentration(
        row.actual_weight for row in rows if row.level == AllocationLevel.CATEGORY
    )

    return AllocationSummary(
        rows=rows,
        invested_value=invested_value,
        cash_value=cash_value,
        total_wealth=total_wealth,
        stale_market_value=stale_market_value,
        unvalued_cost_basis=sum(
            (position.cost_basis for position in unvalued_positions),
            Decimal("0"),
        ),
        unvalued_position_count=len(unvalued_positions),
        concentration=concentration,
    )

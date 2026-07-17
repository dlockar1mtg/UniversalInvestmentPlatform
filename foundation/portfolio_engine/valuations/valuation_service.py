"""Resolve selected valuations for derived positions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from foundation.portfolio_engine.positions.position_builder import DerivedPosition

from .valuation_repository import ValuationRepository
from .valuation_selector import SelectedValuation, select_valuation


def resolve_valuations(
    positions: list[DerivedPosition],
    repository: ValuationRepository,
    *,
    as_of: datetime,
) -> dict[tuple[str, UUID | None], SelectedValuation]:
    selected: dict[tuple[str, UUID | None], SelectedValuation] = {}

    for position in positions:
        history = repository.list_for_asset(
            position.asset_id,
            account_id=position.account_id,
        )
        valuation = select_valuation(
            history,
            liquidity_tier=position.liquidity_tier,
            as_of=as_of,
        )
        if valuation is not None:
            selected[(position.asset_id, position.account_id)] = valuation

    return selected

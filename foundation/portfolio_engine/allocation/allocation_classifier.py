"""Resolve strategy categories for portfolio positions."""

from __future__ import annotations

from dataclasses import replace

from foundation.portfolio_engine.models import AssetCategory
from foundation.portfolio_engine.positions import ValuedPosition


DEFAULT_CLASSIFICATION_OVERRIDES = {
    "GLD": AssetCategory.METALS,
    "IAU": AssetCategory.METALS,
    "SGOL": AssetCategory.METALS,
    "SLV": AssetCategory.METALS,
    "URA": AssetCategory.METALS,
    "CPER": AssetCategory.METALS,
    "BIL": AssetCategory.CASH,
}


def classify_position(
    position: ValuedPosition,
    overrides: dict[str, AssetCategory] | None = None,
) -> ValuedPosition:
    mapping = dict(DEFAULT_CLASSIFICATION_OVERRIDES)
    if overrides:
        mapping.update({key.upper(): value for key, value in overrides.items()})

    resolved = mapping.get(position.asset_id.upper(), position.asset_category)
    if resolved == position.asset_category:
        return position
    return replace(position, asset_category=resolved)


def classify_positions(
    positions: list[ValuedPosition],
    overrides: dict[str, AssetCategory] | None = None,
) -> list[ValuedPosition]:
    return [classify_position(position, overrides) for position in positions]

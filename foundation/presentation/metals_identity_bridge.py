"""Presentation-only identity bridge for certified Metals rich sidecars.

The source artifacts remain immutable. This bridge only projects known commodity
identity variants onto the canonical Metals registry identity used by the active
recommendation catalog and asset-detail API.
"""
from __future__ import annotations

from foundation.production.metals_registry import load_metals_registry

COMMODITY_RICH_FAMILIES = frozenset({
    "model_component",
    "recommendation_change",
    "regime_probability",
    "uncertainty_adjusted",
    "tactical_state",
})


def canonical_presentation_asset_id(family: str, source_asset_id: str) -> str:
    """Return the canonical commodity identity for presentation joins.

    Only explicitly governed commodity-rich families are normalized. Vehicle
    identities and all other source identities remain unchanged.
    """
    raw = str(source_asset_id or "").strip()
    if not raw:
        raise ValueError("Metals presentation asset identity must not be blank")
    if family not in COMMODITY_RICH_FAMILIES:
        return raw

    normalized = raw.lower()
    doubled_prefix = "metals:commodity:metals:commodity:"
    if normalized.startswith(doubled_prefix):
        normalized = "metals:commodity:" + normalized[len(doubled_prefix):]

    prefix = "metals:commodity:"
    if not normalized.startswith(prefix):
        raise ValueError(
            f"Unsupported commodity presentation identity for {family}: {raw}"
        )
    slug = normalized[len(prefix):]
    registry = load_metals_registry()
    asset = registry.assets_by_slug.get(slug)
    if asset is None or asset.asset_class != "commodity":
        raise ValueError(
            f"Unknown canonical Metals commodity identity for {family}: {raw}"
        )
    return asset.asset_id

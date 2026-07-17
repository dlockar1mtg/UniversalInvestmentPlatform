"""Standard asset-class validation limitations."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


DEFAULT_LIMITATIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "crypto": (
            "Shorter institutional history than traditional assets.",
            "High regime sensitivity and exchange-data fragmentation.",
        ),
        "etf": (
            "Fund survivorship and index methodology changes may affect history.",
        ),
        "metals": (
            "Vehicle returns may differ from underlying spot-metal behavior.",
        ),
        "mtg": (
            "Sparse transactions and appraisal-based prices reduce liquidity precision.",
            "Reprint and product-condition effects may not be fully observable historically.",
        ),
        "housing": (
            "Low transaction frequency and geographic aggregation create stale observations.",
            "Transaction costs and financing terms materially affect realized outcomes.",
        ),
        "cash": (
            "Low return dispersion limits rank-correlation usefulness.",
        ),
    }
)


def limitations_for_asset_class(asset_class: str) -> tuple[str, ...]:
    return DEFAULT_LIMITATIONS.get(asset_class, ())

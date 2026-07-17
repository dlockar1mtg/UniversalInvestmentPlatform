"""Registry for normalization strategies."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .normalization_strategy import NormalizationStrategy
from .strategies import (
    BinaryNormalizer,
    BoundedRangeNormalizer,
    CategoricalNormalizer,
    HigherIsBetterNormalizer,
    LowerIsBetterNormalizer,
    PercentileNormalizer,
    PiecewiseNormalizer,
    TargetCenteredNormalizer,
)


class NormalizationRegistry:
    """Mutable-at-construction registry with controlled strategy lookup."""

    def __init__(self) -> None:
        strategies = (
            HigherIsBetterNormalizer(),
            LowerIsBetterNormalizer(),
            BoundedRangeNormalizer(),
            TargetCenteredNormalizer(),
            PercentileNormalizer(),
            BinaryNormalizer(),
            CategoricalNormalizer(),
            PiecewiseNormalizer(),
        )
        self._strategies: dict[str, NormalizationStrategy] = {
            strategy.strategy_name: strategy for strategy in strategies
        }

    @property
    def strategies(self) -> Mapping[str, NormalizationStrategy]:
        return MappingProxyType(self._strategies)

    def register(self, strategy: NormalizationStrategy, *, replace: bool = False) -> None:
        name = strategy.strategy_name
        if name in self._strategies and not replace:
            raise ValueError(f"Normalization strategy already registered: {name}.")
        self._strategies[name] = strategy

    def get(self, strategy_name: str) -> NormalizationStrategy:
        try:
            return self._strategies[strategy_name]
        except KeyError as exc:
            raise KeyError(f"Unknown normalization strategy: {strategy_name}.") from exc


DEFAULT_NORMALIZATION_REGISTRY = NormalizationRegistry()

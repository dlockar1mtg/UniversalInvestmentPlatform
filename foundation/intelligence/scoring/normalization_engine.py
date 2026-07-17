"""Universal normalization orchestration service."""

from __future__ import annotations

from typing import Any

from .normalization import NormalizationResult
from .normalization_registry import (
    DEFAULT_NORMALIZATION_REGISTRY,
    NormalizationRegistry,
)
from .score_component import DataAvailability


class NormalizationEngine:
    """Dispatch normalization requests through the strategy registry."""

    def __init__(
        self,
        registry: NormalizationRegistry = DEFAULT_NORMALIZATION_REGISTRY,
    ) -> None:
        self._registry = registry

    def normalize(
        self,
        strategy_name: str,
        value: Any,
        *,
        availability: DataAvailability = DataAvailability.AVAILABLE,
        warning: str | None = None,
        **parameters: Any,
    ) -> NormalizationResult:
        if availability is not DataAvailability.AVAILABLE:
            return NormalizationResult(
                raw_value=value,
                normalized_score=None,
                strategy=strategy_name,
                availability=availability,
                warning=warning,
                diagnostics=parameters,
            )

        strategy = self._registry.get(strategy_name)
        return strategy.normalize(value, **parameters)

"""Normalization strategy contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from .normalization import NormalizationResult


class NormalizationStrategy(ABC):
    """Abstract interface implemented by all normalization strategies."""

    strategy_name: str

    @abstractmethod
    def normalize(self, value: Any, **parameters: Any) -> NormalizationResult:
        """Normalize a raw value into a 0-100 score."""
        raise NotImplementedError

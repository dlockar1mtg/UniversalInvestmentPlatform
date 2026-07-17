"""Validation profile contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .validation import (
    validate_non_empty_text,
    validate_positive_integer,
    validate_unit_interval,
)


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    """Versioned thresholds and sample requirements for model validation."""

    profile_id: str
    version: str
    minimum_observations: int
    minimum_assets: int
    minimum_date_coverage: Decimal
    rank_metrics: tuple[str, ...]
    performance_metrics: tuple[str, ...]
    thresholds: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_id",
            validate_non_empty_text(self.profile_id, "profile_id"),
        )
        object.__setattr__(
            self,
            "version",
            validate_non_empty_text(self.version, "version"),
        )
        object.__setattr__(
            self,
            "minimum_observations",
            validate_positive_integer(
                self.minimum_observations,
                "minimum_observations",
            ),
        )
        object.__setattr__(
            self,
            "minimum_assets",
            validate_positive_integer(self.minimum_assets, "minimum_assets"),
        )
        object.__setattr__(
            self,
            "minimum_date_coverage",
            validate_unit_interval(
                self.minimum_date_coverage,
                "minimum_date_coverage",
            ),
        )
        if not self.rank_metrics:
            raise ValueError("rank_metrics must not be empty.")
        if not self.performance_metrics:
            raise ValueError("performance_metrics must not be empty.")
        object.__setattr__(
            self,
            "rank_metrics",
            tuple(
                validate_non_empty_text(item, "rank metric")
                for item in self.rank_metrics
            ),
        )
        object.__setattr__(
            self,
            "performance_metrics",
            tuple(
                validate_non_empty_text(item, "performance metric")
                for item in self.performance_metrics
            ),
        )
        normalized = {
            validate_non_empty_text(name, "threshold name"): Decimal(str(value))
            for name, value in self.thresholds.items()
        }
        object.__setattr__(self, "thresholds", MappingProxyType(normalized))

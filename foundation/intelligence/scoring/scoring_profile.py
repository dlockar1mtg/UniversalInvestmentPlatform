"""Asset-class scoring profile contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .score_dimension import ScoreDimension
from .validation import (
    validate_non_empty_text,
    validate_unit_interval,
    validate_weight_total,
)


@dataclass(frozen=True, slots=True)
class ScoringProfile:
    """Versioned weights and policy settings for one asset class."""

    profile_id: str
    asset_class: str
    version: str
    dimension_weights: Mapping[ScoreDimension, Decimal]
    minimum_coverage: Decimal
    confidence_floor: Decimal
    maximum_risk_penalty: Decimal
    status: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "profile_id", validate_non_empty_text(self.profile_id, "profile_id")
        )
        object.__setattr__(
            self, "asset_class", validate_non_empty_text(self.asset_class, "asset_class")
        )
        object.__setattr__(self, "version", validate_non_empty_text(self.version, "version"))
        object.__setattr__(self, "status", validate_non_empty_text(self.status, "status"))

        if not self.dimension_weights:
            raise ValueError("dimension_weights must not be empty.")

        normalized: dict[ScoreDimension, Decimal] = {}
        for dimension, weight in self.dimension_weights.items():
            if not isinstance(dimension, ScoreDimension):
                raise TypeError(
                    "dimension_weights keys must be ScoreDimension values."
                )
            normalized[dimension] = validate_unit_interval(
                weight, f"dimension_weights[{dimension.value}]"
            )
        validate_weight_total(normalized)
        object.__setattr__(
            self, "dimension_weights", MappingProxyType(normalized)
        )
        object.__setattr__(
            self,
            "minimum_coverage",
            validate_unit_interval(self.minimum_coverage, "minimum_coverage"),
        )
        object.__setattr__(
            self,
            "confidence_floor",
            validate_unit_interval(self.confidence_floor, "confidence_floor"),
        )
        object.__setattr__(
            self,
            "maximum_risk_penalty",
            validate_unit_interval(
                self.maximum_risk_penalty, "maximum_risk_penalty"
            ),
        )

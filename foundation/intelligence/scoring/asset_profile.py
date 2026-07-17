"""Asset-class scoring profile definitions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .score_dimension import ScoreDimension
from .scoring_profile import ScoringProfile
from .validation import validate_non_empty_text, validate_unit_interval


@dataclass(frozen=True, slots=True)
class MetricNormalizationRule:
    """Normalization and weighting rule for one asset-class metric."""

    metric_name: str
    dimension: ScoreDimension
    strategy: str
    weight: Decimal
    confidence: Decimal
    parameters: Mapping[str, Any] | None = None
    source_field: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_name",
            validate_non_empty_text(self.metric_name, "metric_name"),
        )
        object.__setattr__(
            self,
            "strategy",
            validate_non_empty_text(self.strategy, "strategy"),
        )
        object.__setattr__(
            self,
            "weight",
            validate_unit_interval(self.weight, "weight"),
        )
        object.__setattr__(
            self,
            "confidence",
            validate_unit_interval(self.confidence, "confidence"),
        )
        if self.source_field is not None:
            object.__setattr__(
                self,
                "source_field",
                validate_non_empty_text(self.source_field, "source_field"),
            )
        if self.description:
            object.__setattr__(
                self,
                "description",
                validate_non_empty_text(self.description, "description"),
            )
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(dict(self.parameters or {})),
        )


@dataclass(frozen=True, slots=True)
class AssetClassScoringProfile:
    """Complete versioned scoring configuration for one asset class."""

    model_id: str
    scoring_profile: ScoringProfile
    normalization_profile_id: str
    metric_rules: tuple[MetricNormalizationRule, ...]
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "model_id",
            validate_non_empty_text(self.model_id, "model_id"),
        )
        object.__setattr__(
            self,
            "normalization_profile_id",
            validate_non_empty_text(
                self.normalization_profile_id,
                "normalization_profile_id",
            ),
        )
        if not self.metric_rules:
            raise ValueError("metric_rules must not be empty.")
        names = [rule.metric_name for rule in self.metric_rules]
        if len(names) != len(set(names)):
            raise ValueError("Metric rule names must be unique.")
        unsupported = {
            rule.dimension
            for rule in self.metric_rules
            if rule.dimension not in self.scoring_profile.dimension_weights
        }
        if unsupported:
            names = ", ".join(sorted(item.value for item in unsupported))
            raise ValueError(f"Metric rules use unsupported dimensions: {names}.")
        if self.description:
            object.__setattr__(
                self,
                "description",
                validate_non_empty_text(self.description, "description"),
            )

    @property
    def asset_class(self) -> str:
        return self.scoring_profile.asset_class

"""Scoring request contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .score_component import ScoreComponent
from .scoring_profile import ScoringProfile
from .validation import validate_non_empty_text


@dataclass(frozen=True, slots=True)
class ScoreInput:
    """Complete deterministic input submitted to a scoring engine."""

    asset_id: str
    asset_class: str
    as_of_date: date
    profile: ScoringProfile
    components: tuple[ScoreComponent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "asset_id", validate_non_empty_text(self.asset_id, "asset_id")
        )
        object.__setattr__(
            self, "asset_class", validate_non_empty_text(self.asset_class, "asset_class")
        )
        if not isinstance(self.as_of_date, date):
            raise TypeError("as_of_date must be a datetime.date.")
        if self.asset_class != self.profile.asset_class:
            raise ValueError("asset_class must match profile.asset_class.")
        if not self.components:
            raise ValueError("At least one score component is required.")
        metric_names = [component.metric_name for component in self.components]
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("Score component metric names must be unique.")
        unsupported = {
            component.dimension
            for component in self.components
            if component.dimension not in self.profile.dimension_weights
        }
        if unsupported:
            names = ", ".join(sorted(item.value for item in unsupported))
            raise ValueError(f"Components include unsupported dimensions: {names}.")

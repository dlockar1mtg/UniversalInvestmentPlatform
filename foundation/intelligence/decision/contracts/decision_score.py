"""Universal decision score contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .decision_errors import DecisionValidationError


@dataclass(frozen=True, slots=True)
class DecisionScore:
    """Transparent score produced by the decision scoring pipeline."""

    base_score: float
    penalty_score: float
    final_score: float
    component_scores: Mapping[str, float] = field(default_factory=dict)
    penalty_components: Mapping[str, float] = field(default_factory=dict)
    scoring_version: str = "5.1.1"

    def __post_init__(self) -> None:
        self._validate_score("base_score", self.base_score)
        self._validate_score("penalty_score", self.penalty_score)
        self._validate_score("final_score", self.final_score)

        for name, score in self.component_scores.items():
            if not str(name).strip():
                raise DecisionValidationError(
                    "Component score names cannot be empty."
                )
            self._validate_score(
                f"component_scores[{name!r}]",
                score,
            )

        for name, penalty in self.penalty_components.items():
            if not str(name).strip():
                raise DecisionValidationError(
                    "Penalty component names cannot be empty."
                )
            self._validate_score(
                f"penalty_components[{name!r}]",
                penalty,
            )

        if not self.scoring_version.strip():
            raise DecisionValidationError(
                "scoring_version cannot be empty."
            )

    @staticmethod
    def _validate_score(name: str, value: float) -> None:
        if not 0.0 <= float(value) <= 100.0:
            raise DecisionValidationError(
                f"{name} must be between 0.0 and 100.0."
            )

"""Evidence records supporting a decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from .decision_errors import DecisionValidationError


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    """A traceable piece of evidence used by the decision engine."""

    evidence_id: str
    category: str
    source: str
    description: str
    value: float | int | str | bool | None = None
    weight: float = 1.0
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise DecisionValidationError("evidence_id cannot be empty.")

        if not self.category.strip():
            raise DecisionValidationError("category cannot be empty.")

        if not self.source.strip():
            raise DecisionValidationError("source cannot be empty.")

        if not self.description.strip():
            raise DecisionValidationError("description cannot be empty.")

        if not 0.0 <= self.weight <= 1.0:
            raise DecisionValidationError(
                "Evidence weight must be between 0.0 and 1.0."
            )

        if self.observed_at.tzinfo is None:
            raise DecisionValidationError(
                "observed_at must include timezone information."
            )

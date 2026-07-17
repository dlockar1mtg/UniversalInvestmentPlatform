"""Versioned scoring model registration contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .score_dimension import ScoreDimension
from .validation import validate_non_empty_text


class ScoringModelStatus(str, Enum):
    """Lifecycle status for a registered scoring model."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ScoringModelDefinition:
    """Single source of truth for selecting and reproducing a scoring model."""

    model_id: str
    asset_class: str
    version: str
    scoring_profile_id: str
    normalization_profile_id: str
    status: ScoringModelStatus
    effective_from: date
    effective_to: date | None = None
    description: str = ""
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "model_id",
            "asset_class",
            "version",
            "scoring_profile_id",
            "normalization_profile_id",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )

        if not isinstance(self.status, ScoringModelStatus):
            raise TypeError("status must be a ScoringModelStatus.")
        if not isinstance(self.effective_from, date):
            raise TypeError("effective_from must be a datetime.date.")
        if self.effective_to is not None:
            if not isinstance(self.effective_to, date):
                raise TypeError("effective_to must be a datetime.date or None.")
            if self.effective_to < self.effective_from:
                raise ValueError("effective_to must not be before effective_from.")

        if self.description:
            object.__setattr__(
                self,
                "description",
                validate_non_empty_text(self.description, "description"),
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata or {})),
        )

    @property
    def registry_key(self) -> tuple[str, str]:
        return self.model_id, self.version

    def is_effective_on(self, as_of_date: date) -> bool:
        """Return whether the model is effective on the supplied date."""
        if not isinstance(as_of_date, date):
            raise TypeError("as_of_date must be a datetime.date.")
        if as_of_date < self.effective_from:
            return False
        return self.effective_to is None or as_of_date <= self.effective_to

    def supports_dimension(self, dimension: ScoreDimension) -> bool:
        """Optional metadata-based dimension support check."""
        configured = self.metadata.get("dimensions")
        if configured is None:
            return True
        values = {
            item.value if isinstance(item, ScoreDimension) else str(item)
            for item in configured
        }
        return dimension.value in values

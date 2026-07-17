"""Historical prediction record contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .validation import (
    validate_non_empty_text,
    validate_score,
    validate_unit_interval,
)


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """Score generated at a historical point in time."""

    asset_id: str
    asset_class: str
    prediction_date: date
    model_id: str
    model_version: str
    final_score: Decimal
    score_band: str
    confidence_score: Decimal
    coverage_ratio: Decimal
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "asset_id",
            "asset_class",
            "model_id",
            "model_version",
            "score_band",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.prediction_date, date):
            raise TypeError("prediction_date must be a datetime.date.")
        object.__setattr__(
            self,
            "final_score",
            validate_score(self.final_score, "final_score"),
        )
        object.__setattr__(
            self,
            "confidence_score",
            validate_score(self.confidence_score, "confidence_score"),
        )
        object.__setattr__(
            self,
            "coverage_ratio",
            validate_unit_interval(self.coverage_ratio, "coverage_ratio"),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata or {})),
        )

"""Historical validation result contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .validation import validate_non_empty_text, validate_positive_integer


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Immutable output produced by a validation run."""

    validation_run_id: str
    backtest_id: str
    model_id: str
    model_version: str
    horizon_days: int
    observation_count: int
    asset_count: int
    metrics: Mapping[str, Decimal]
    passed: bool
    generated_at: datetime
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "validation_run_id",
            "backtest_id",
            "model_id",
            "model_version",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "horizon_days",
            validate_positive_integer(self.horizon_days, "horizon_days"),
        )
        object.__setattr__(
            self,
            "observation_count",
            validate_positive_integer(
                self.observation_count,
                "observation_count",
            ),
        )
        object.__setattr__(
            self,
            "asset_count",
            validate_positive_integer(self.asset_count, "asset_count"),
        )
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be a bool.")
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime.datetime.")
        normalized_metrics = {
            validate_non_empty_text(name, "metric name"): Decimal(str(value))
            for name, value in self.metrics.items()
        }
        if not normalized_metrics:
            raise ValueError("metrics must not be empty.")
        object.__setattr__(
            self,
            "metrics",
            MappingProxyType(normalized_metrics),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(
                validate_non_empty_text(item, "warning")
                for item in self.warnings
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata or {})),
        )

"""Walk-forward backtest configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from .validation import (
    validate_horizons,
    validate_non_empty_text,
    validate_positive_integer,
    validate_score,
    validate_unit_interval,
)


class RebalanceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass(frozen=True, slots=True)
class BacktestConfiguration:
    """Immutable configuration for historical walk-forward validation."""

    backtest_id: str
    model_id: str
    model_version: str
    asset_class: str
    start_date: date
    end_date: date
    horizons_days: tuple[int, ...]
    rebalance_frequency: RebalanceFrequency
    minimum_score: Decimal = Decimal("0")
    minimum_confidence: Decimal = Decimal("0")
    minimum_coverage: Decimal = Decimal("0")
    benchmark_id: str | None = None
    warmup_days: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "backtest_id",
            "model_id",
            "model_version",
            "asset_class",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise TypeError("start_date and end_date must be datetime.date values.")
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date.")
        if not isinstance(self.rebalance_frequency, RebalanceFrequency):
            raise TypeError("rebalance_frequency must be a RebalanceFrequency.")
        object.__setattr__(
            self,
            "horizons_days",
            validate_horizons(self.horizons_days),
        )
        object.__setattr__(
            self,
            "minimum_score",
            validate_score(self.minimum_score, "minimum_score"),
        )
        object.__setattr__(
            self,
            "minimum_confidence",
            validate_score(self.minimum_confidence, "minimum_confidence"),
        )
        object.__setattr__(
            self,
            "minimum_coverage",
            validate_unit_interval(self.minimum_coverage, "minimum_coverage"),
        )
        if self.benchmark_id is not None:
            object.__setattr__(
                self,
                "benchmark_id",
                validate_non_empty_text(self.benchmark_id, "benchmark_id"),
            )
        if isinstance(self.warmup_days, bool) or not isinstance(self.warmup_days, int):
            raise TypeError("warmup_days must be an integer.")
        if self.warmup_days < 0:
            raise ValueError("warmup_days must be non-negative.")

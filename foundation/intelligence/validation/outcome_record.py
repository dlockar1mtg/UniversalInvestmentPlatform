"""Realized forward outcome contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .validation import to_decimal, validate_non_empty_text, validate_positive_integer


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """Observed forward return and risk outcome for one prediction horizon."""

    asset_id: str
    prediction_date: date
    horizon_days: int
    outcome_date: date
    starting_price: Decimal
    ending_price: Decimal
    total_return: Decimal
    benchmark_return: Decimal | None = None
    maximum_drawdown: Decimal | None = None
    source: str = "unknown"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "asset_id",
            validate_non_empty_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "source",
            validate_non_empty_text(self.source, "source"),
        )
        if not isinstance(self.prediction_date, date):
            raise TypeError("prediction_date must be a datetime.date.")
        if not isinstance(self.outcome_date, date):
            raise TypeError("outcome_date must be a datetime.date.")
        if self.outcome_date <= self.prediction_date:
            raise ValueError("outcome_date must be after prediction_date.")
        object.__setattr__(
            self,
            "horizon_days",
            validate_positive_integer(self.horizon_days, "horizon_days"),
        )
        for field_name in ("starting_price", "ending_price", "total_return"):
            object.__setattr__(
                self,
                field_name,
                to_decimal(getattr(self, field_name), field_name),
            )
        if self.starting_price <= Decimal("0"):
            raise ValueError("starting_price must be greater than zero.")
        if self.ending_price < Decimal("0"):
            raise ValueError("ending_price must be non-negative.")
        if self.benchmark_return is not None:
            object.__setattr__(
                self,
                "benchmark_return",
                to_decimal(self.benchmark_return, "benchmark_return"),
            )
        if self.maximum_drawdown is not None:
            drawdown = to_decimal(self.maximum_drawdown, "maximum_drawdown")
            if drawdown > Decimal("0"):
                raise ValueError("maximum_drawdown must be zero or negative.")
            object.__setattr__(self, "maximum_drawdown", drawdown)

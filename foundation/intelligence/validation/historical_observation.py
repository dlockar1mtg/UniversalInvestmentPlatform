"""Historical market observation contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .validation import to_decimal, validate_non_empty_text


@dataclass(frozen=True, slots=True)
class HistoricalObservation:
    """Point-in-time market data available to a model on an observation date."""

    asset_id: str
    asset_class: str
    observation_date: date
    price: Decimal | None
    features: Mapping[str, Any]
    source: str
    data_version: str

    def __post_init__(self) -> None:
        for field_name in ("asset_id", "asset_class", "source", "data_version"):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.observation_date, date):
            raise TypeError("observation_date must be a datetime.date.")
        if self.price is not None:
            price = to_decimal(self.price, "price")
            if price < Decimal("0"):
                raise ValueError("price must be non-negative.")
            object.__setattr__(self, "price", price)
        object.__setattr__(
            self,
            "features",
            MappingProxyType(dict(self.features)),
        )

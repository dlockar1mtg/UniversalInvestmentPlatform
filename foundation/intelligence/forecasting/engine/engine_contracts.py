"""Contracts used by the universal forecast engine lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from ..models import ForecastHorizon, UniversalForecast


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class ForecastExecutionStatus(str, Enum):
    """Lifecycle result for one engine execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class ForecastEngineError(RuntimeError):
    """Base exception for forecast engine failures."""


class ForecastValidationError(ForecastEngineError):
    """Raised when a request or forecast fails validation."""


class ForecastExecutionError(ForecastEngineError):
    """Raised when model execution cannot produce a valid forecast."""


@dataclass(frozen=True, slots=True)
class ForecastEngineMetadata:
    """Descriptive metadata exposed by a forecast engine."""

    engine_name: str
    engine_version: str
    asset_classes: tuple[str, ...]
    supported_horizons: tuple[ForecastHorizon, ...]
    description: str = ""
    deterministic: bool = True
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.engine_name.strip():
            raise ValueError("engine_name is required.")
        if not self.engine_version.strip():
            raise ValueError("engine_version is required.")
        if not self.asset_classes:
            raise ValueError("asset_classes cannot be empty.")
        if not self.supported_horizons:
            raise ValueError("supported_horizons cannot be empty.")
        if len(set(self.asset_classes)) != len(self.asset_classes):
            raise ValueError("asset_classes cannot contain duplicates.")
        if len(set(self.supported_horizons)) != len(self.supported_horizons):
            raise ValueError("supported_horizons cannot contain duplicates.")


@dataclass(frozen=True, slots=True)
class ForecastRequest:
    """Canonical input passed to every forecast engine."""

    asset_id: str
    asset_class: str
    as_of_date: date
    horizon: ForecastHorizon
    reference_value: float
    currency: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    target_date: date | None = None
    features: Mapping[str, Any] = field(default_factory=dict)
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id is required.")
        if not self.asset_id.strip():
            raise ValueError("asset_id is required.")
        if not self.asset_class.strip():
            raise ValueError("asset_class is required.")
        if not self.currency.strip():
            raise ValueError("currency is required.")
        if self.reference_value < 0:
            raise ValueError("reference_value cannot be negative.")
        if self.target_date is not None and self.target_date <= self.as_of_date:
            raise ValueError("target_date must be after as_of_date.")

        object.__setattr__(self, "features", _freeze_mapping(self.features))
        object.__setattr__(self, "options", _freeze_mapping(self.options))


@dataclass(frozen=True, slots=True)
class ForecastExecutionResult:
    """Auditable result of one forecast request execution."""

    request_id: str
    engine_name: str
    engine_version: str
    status: ForecastExecutionStatus
    started_at: datetime
    completed_at: datetime
    forecast: UniversalForecast | None = None
    error_type: str | None = None
    error_message: str | None = None
    warnings: tuple[str, ...] = ()
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("Execution timestamps must be timezone-aware.")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at.")

        if self.status is ForecastExecutionStatus.SUCCEEDED:
            if self.forecast is None:
                raise ValueError("Successful execution requires a forecast.")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("Successful execution cannot contain an error.")
        else:
            if self.forecast is not None:
                raise ValueError("Failed or rejected execution cannot contain a forecast.")
            if not self.error_message:
                raise ValueError("Failed or rejected execution requires error_message.")

        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))

    @property
    def duration_seconds(self) -> float:
        """Execution duration in seconds."""

        return (self.completed_at - self.started_at).total_seconds()

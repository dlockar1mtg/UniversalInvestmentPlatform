"""Execution context shared across forecast engine lifecycle hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import Logger, getLogger
from random import Random
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(slots=True)
class ForecastExecutionContext:
    """Runtime services available to a forecast engine."""

    logger: Logger = field(
        default_factory=lambda: getLogger(
            "foundation.intelligence.forecasting"
        )
    )
    random_seed: int | None = None
    services: Mapping[str, Any] = field(default_factory=dict)
    execution_started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.execution_started_at.tzinfo is None:
            raise ValueError("execution_started_at must be timezone-aware.")
        self.services = MappingProxyType(dict(self.services))

    def create_random(self) -> Random:
        """Return a request-scoped pseudo-random generator."""

        return Random(self.random_seed)

    def get_service(self, name: str) -> Any:
        """Resolve a named runtime service."""

        try:
            return self.services[name]
        except KeyError as exc:
            raise KeyError(f"Execution service not found: {name}") from exc

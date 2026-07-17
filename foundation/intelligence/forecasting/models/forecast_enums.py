"""Enumerations shared by all universal forecasting models."""

from __future__ import annotations

from enum import Enum


class StringEnum(str, Enum):
    """Enum whose members serialize naturally as strings."""

    def __str__(self) -> str:
        return self.value


class ForecastHorizon(StringEnum):
    """Canonical forecast horizons supported by the platform."""

    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    THREE_YEARS = "3y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"

    @property
    def approximate_days(self) -> int:
        """Return the normalized number of days used for comparisons."""

        return {
            ForecastHorizon.ONE_DAY: 1,
            ForecastHorizon.ONE_WEEK: 7,
            ForecastHorizon.ONE_MONTH: 30,
            ForecastHorizon.THREE_MONTHS: 91,
            ForecastHorizon.SIX_MONTHS: 182,
            ForecastHorizon.ONE_YEAR: 365,
            ForecastHorizon.THREE_YEARS: 1_095,
            ForecastHorizon.FIVE_YEARS: 1_825,
            ForecastHorizon.TEN_YEARS: 3_650,
        }[self]


class ForecastScenario(StringEnum):
    """Standard scenario names used across all asset classes."""

    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


class ForecastDirection(StringEnum):
    """Expected movement relative to the forecast's reference value."""

    STRONGLY_DOWN = "strongly_down"
    DOWN = "down"
    FLAT = "flat"
    UP = "up"
    STRONGLY_UP = "strongly_up"
    UNKNOWN = "unknown"


class ForecastMethod(StringEnum):
    """Broad method family responsible for a forecast."""

    STATISTICAL = "statistical"
    MACHINE_LEARNING = "machine_learning"
    MONTE_CARLO = "monte_carlo"
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    RULE_BASED = "rule_based"
    ENSEMBLE = "ensemble"
    EXTERNAL = "external"


class ForecastStatus(StringEnum):
    """Lifecycle and quality state of a generated forecast."""

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class IntervalType(StringEnum):
    """Meaning of a lower/upper uncertainty interval."""

    CONFIDENCE = "confidence"
    PREDICTION = "prediction"
    CREDIBLE = "credible"
    QUANTILE = "quantile"

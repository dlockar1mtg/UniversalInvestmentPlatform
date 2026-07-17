"""Universal forecast model contracts.

This package defines the shared enums, schema objects, and validation helpers
used by every forecasting implementation in the Universal Investment
Intelligence Platform.
"""

from .forecast_enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastScenario,
    ForecastStatus,
    IntervalType,
)
from .forecast_models import (
    ForecastDistribution,
    ForecastInterval,
    ForecastProvenance,
    ForecastScenarioResult,
    UniversalForecast,
)
from .forecast_schema import (
    FORECAST_SCHEMA_NAME,
    FORECAST_SCHEMA_VERSION,
    ForecastSchemaError,
    forecast_from_dict,
    forecast_to_dict,
    validate_forecast,
    validate_forecast_payload,
)

__all__ = [
    "FORECAST_SCHEMA_NAME",
    "FORECAST_SCHEMA_VERSION",
    "ForecastDirection",
    "ForecastDistribution",
    "ForecastHorizon",
    "ForecastInterval",
    "ForecastMethod",
    "ForecastProvenance",
    "ForecastScenario",
    "ForecastScenarioResult",
    "ForecastSchemaError",
    "ForecastStatus",
    "IntervalType",
    "UniversalForecast",
    "forecast_from_dict",
    "forecast_to_dict",
    "validate_forecast",
    "validate_forecast_payload",
]

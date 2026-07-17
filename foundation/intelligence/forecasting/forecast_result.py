from dataclasses import dataclass
from typing import Any
from .forecast_types import ForecastType
from .horizons import ForecastHorizon
from .forecast_metadata import ForecastMetadata

@dataclass(frozen=True)
class ForecastResult:
    asset_id:str
    forecast_date:str
    forecast_horizon:ForecastHorizon
    forecast_type:ForecastType
    expected_value:float
    expected_return:float
    confidence:float
    lower_bound:float
    upper_bound:float
    distribution:Any
    risk_metrics:dict
    diagnostics:dict
    metadata:ForecastMetadata

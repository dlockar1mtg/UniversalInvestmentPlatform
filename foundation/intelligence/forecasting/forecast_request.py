from dataclasses import dataclass, field
from typing import Any
from .forecast_types import ForecastType
from .horizons import ForecastHorizon

@dataclass(frozen=True)
class ForecastRequest:
    asset_id:str
    platform:str
    forecast_type:ForecastType
    forecast_horizon:ForecastHorizon
    historical_data:Any
    current_state:Any
    requested_model:str
    parameters:dict[str,Any]=field(default_factory=dict)
    random_seed:int|None=None

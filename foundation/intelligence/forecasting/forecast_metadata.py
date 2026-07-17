from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

@dataclass(frozen=True)
class ForecastMetadata:
    model_name:str
    model_version:str
    framework_version:str
    training_start:datetime|None=None
    training_end:datetime|None=None
    historical_rows:int=0
    runtime_seconds:float=0.0
    random_seed:int|None=None
    platform:str=""
    generated_by:str=""
    notes:str=""
    forecast_uuid:str=field(default_factory=lambda:str(uuid4()))
    generated_timestamp:datetime=field(default_factory=datetime.utcnow)

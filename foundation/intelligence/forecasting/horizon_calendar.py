from datetime import datetime, timedelta
from .forecast_horizon_engine import ForecastHorizonEngine

def forecast_end_date(start: datetime, horizon):
    return start + timedelta(days=ForecastHorizonEngine.days(horizon))

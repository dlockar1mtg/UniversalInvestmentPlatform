from .horizons import ForecastHorizon

def validate_horizon(value):
    if not isinstance(value, ForecastHorizon):
        raise ValueError("Invalid ForecastHorizon")
    return True

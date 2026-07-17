"""
Phase 4.2 Forecast Horizon Engine
"""
from .horizons import ForecastHorizon, HORIZON_INFO

class ForecastHorizonEngine:
    """Utility methods for working with forecast horizons."""

    @staticmethod
    def days(horizon: ForecastHorizon)->int:
        return HORIZON_INFO[horizon].days

    @staticmethod
    def months(horizon: ForecastHorizon)->float:
        return HORIZON_INFO[horizon].months

    @staticmethod
    def annualization_factor(horizon: ForecastHorizon)->float:
        return HORIZON_INFO[horizon].annualization_factor

    @staticmethod
    def ordered():
        return list(ForecastHorizon)

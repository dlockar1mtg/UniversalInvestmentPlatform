from .forecast_horizon_engine import ForecastHorizonEngine

class HorizonScaling:
    @staticmethod
    def annualize_return(period_return: float, horizon):
        return period_return * ForecastHorizonEngine.annualization_factor(horizon)

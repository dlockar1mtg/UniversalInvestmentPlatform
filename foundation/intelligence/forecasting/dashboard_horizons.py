from .forecast_horizon_engine import ForecastHorizonEngine

def dashboard_rows():
    return [
        {
            "horizon":h.value,
            "days":ForecastHorizonEngine.days(h),
            "months":ForecastHorizonEngine.months(h)
        }
        for h in ForecastHorizonEngine.ordered()
    ]

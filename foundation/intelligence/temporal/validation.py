from .horizon_registry import Horizon
def validate_horizon(h):
    if not isinstance(h,Horizon):
        raise ValueError("Invalid horizon")
    return True

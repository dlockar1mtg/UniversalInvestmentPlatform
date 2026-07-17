from dataclasses import dataclass
from enum import Enum

class Horizon(str, Enum):
    ONE_DAY="ONE_DAY"; ONE_WEEK="ONE_WEEK"; TWO_WEEKS="TWO_WEEKS"
    ONE_MONTH="ONE_MONTH"; THREE_MONTHS="THREE_MONTHS"; SIX_MONTHS="SIX_MONTHS"
    ONE_YEAR="ONE_YEAR"; TWO_YEARS="TWO_YEARS"; THREE_YEARS="THREE_YEARS"
    FIVE_YEARS="FIVE_YEARS"; TEN_YEARS="TEN_YEARS"

@dataclass(frozen=True)
class HorizonInfo:
    calendar_days:int
    business_days:int
    trading_days:int
    months:float
    annualization_factor:float

_registry={
    Horizon.ONE_DAY:HorizonInfo(1,1,1,1/30,365),
    Horizon.ONE_WEEK:HorizonInfo(7,5,5,7/30,52.14),
    Horizon.TWO_WEEKS:HorizonInfo(14,10,10,14/30,26.07),
    Horizon.ONE_MONTH:HorizonInfo(30,22,21,1,12),
    Horizon.THREE_MONTHS:HorizonInfo(90,66,63,3,4),
    Horizon.SIX_MONTHS:HorizonInfo(180,132,126,6,2),
    Horizon.ONE_YEAR:HorizonInfo(365,260,252,12,1),
    Horizon.TWO_YEARS:HorizonInfo(730,520,504,24,.5),
    Horizon.THREE_YEARS:HorizonInfo(1095,780,756,36,.3333),
    Horizon.FIVE_YEARS:HorizonInfo(1825,1300,1260,60,.2),
    Horizon.TEN_YEARS:HorizonInfo(3650,2600,2520,120,.1)
}
class HorizonRegistry:
    @staticmethod
    def get(h): return _registry[h]
    @staticmethod
    def all(): return _registry.copy()

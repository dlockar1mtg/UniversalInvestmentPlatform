from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class HorizonInfo:
    days:int
    months:float
    annualization_factor:float

class ForecastHorizon(str, Enum):
    ONE_DAY="ONE_DAY"
    ONE_WEEK="ONE_WEEK"
    TWO_WEEKS="TWO_WEEKS"
    ONE_MONTH="ONE_MONTH"
    THREE_MONTHS="THREE_MONTHS"
    SIX_MONTHS="SIX_MONTHS"
    ONE_YEAR="ONE_YEAR"
    TWO_YEARS="TWO_YEARS"
    THREE_YEARS="THREE_YEARS"
    FIVE_YEARS="FIVE_YEARS"
    TEN_YEARS="TEN_YEARS"

HORIZON_INFO={
    ForecastHorizon.ONE_DAY:HorizonInfo(1,1/30,365),
    ForecastHorizon.ONE_WEEK:HorizonInfo(7,7/30,365/7),
    ForecastHorizon.TWO_WEEKS:HorizonInfo(14,14/30,365/14),
    ForecastHorizon.ONE_MONTH:HorizonInfo(30,1,12),
    ForecastHorizon.THREE_MONTHS:HorizonInfo(90,3,4),
    ForecastHorizon.SIX_MONTHS:HorizonInfo(180,6,2),
    ForecastHorizon.ONE_YEAR:HorizonInfo(365,12,1),
    ForecastHorizon.TWO_YEARS:HorizonInfo(730,24,0.5),
    ForecastHorizon.THREE_YEARS:HorizonInfo(1095,36,1/3),
    ForecastHorizon.FIVE_YEARS:HorizonInfo(1825,60,0.2),
    ForecastHorizon.TEN_YEARS:HorizonInfo(3650,120,0.1),
}

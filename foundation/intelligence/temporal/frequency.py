from enum import Enum
class Frequency(str, Enum):
    DAILY="DAILY"
    BUSINESS_DAILY="BUSINESS_DAILY"
    WEEKLY="WEEKLY"
    MONTHLY="MONTHLY"
    QUARTERLY="QUARTERLY"
    YEARLY="YEARLY"

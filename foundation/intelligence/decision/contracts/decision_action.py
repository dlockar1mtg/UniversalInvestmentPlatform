"""Actions produced by the Universal Decision Engine."""

from enum import StrEnum


class DecisionAction(StrEnum):
    """Standard action vocabulary shared across all asset classes."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    ACCUMULATE = "accumulate"
    HOLD = "hold"
    WAIT = "wait"
    REDUCE = "reduce"
    SELL = "sell"
    AVOID = "avoid"
    INELIGIBLE = "ineligible"
    INSUFFICIENT_DATA = "insufficient_data"

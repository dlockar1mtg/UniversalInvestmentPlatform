"""Universal eligibility and data-quality evaluation."""

from .eligibility_check import EligibilityCheck
from .eligibility_engine import UniversalEligibilityEngine
from .eligibility_result import EligibilityResult

__all__ = [
    "EligibilityCheck",
    "EligibilityResult",
    "UniversalEligibilityEngine",
]

"""Universal single-decision capital allocation."""

from .allocation_engine import UniversalAllocationEngine
from .allocation_errors import (
    AllocationConfigurationError,
    AllocationInputError,
    AllocationRecommendationError,
)
from .allocation_profile import AllocationProfile
from .allocation_result import AllocationResult

__all__ = [
    "AllocationConfigurationError",
    "AllocationInputError",
    "AllocationProfile",
    "AllocationRecommendationError",
    "AllocationResult",
    "UniversalAllocationEngine",
]

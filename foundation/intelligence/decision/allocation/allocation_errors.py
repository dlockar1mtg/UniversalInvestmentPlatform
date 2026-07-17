"""Exceptions raised by single-decision allocation."""


class AllocationRecommendationError(ValueError):
    """Base exception for allocation-recommendation failures."""


class AllocationConfigurationError(AllocationRecommendationError):
    """Raised when an allocation profile is invalid."""


class AllocationInputError(AllocationRecommendationError):
    """Raised when allocation inputs are inconsistent."""

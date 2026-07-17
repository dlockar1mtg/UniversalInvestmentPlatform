"""Exceptions raised by confidence aggregation."""


class ConfidenceAggregationError(ValueError):
    """Base exception for confidence aggregation failures."""


class ConfidenceConfigurationError(ConfidenceAggregationError):
    """Raised when a confidence profile is invalid."""


class ConfidenceInputError(ConfidenceAggregationError):
    """Raised when confidence inputs are inconsistent or invalid."""

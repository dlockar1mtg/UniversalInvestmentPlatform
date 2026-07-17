"""Exceptions raised by decision constraint evaluation."""


class ConstraintEvaluationError(ValueError):
    """Base exception for constraint-evaluation failures."""


class ConstraintInputError(ConstraintEvaluationError):
    """Raised when decision artifacts are inconsistent."""

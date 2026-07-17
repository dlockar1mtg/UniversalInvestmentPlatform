"""Exceptions raised by universal decision scoring."""


class DecisionScoringError(ValueError):
    """Base exception for decision-scoring failures."""


class IneligibleScoringError(DecisionScoringError):
    """Raised when an opportunity is not permitted to enter scoring."""


class ScoringConfigurationError(DecisionScoringError):
    """Raised when a scoring profile is invalid."""

"""Exceptions raised by universal decision explanation."""


class DecisionExplanationError(ValueError):
    """Base exception for explanation-generation failures."""


class ExplanationInputError(DecisionExplanationError):
    """Raised when explanation artifacts are inconsistent."""


class ExplanationConfigurationError(DecisionExplanationError):
    """Raised when an explanation profile is invalid."""

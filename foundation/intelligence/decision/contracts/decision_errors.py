"""Custom exceptions raised by decision contracts."""


class DecisionContractError(ValueError):
    """Base exception for invalid decision contract data."""


class DecisionValidationError(DecisionContractError):
    """Raised when a decision contract fails validation."""


class DecisionPolicyError(DecisionContractError):
    """Raised when a decision policy is internally inconsistent."""

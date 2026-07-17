"""
Exceptions for Universal Decision Engine certification.
"""

class DecisionCertificationError(RuntimeError):
    """Base certification exception."""

class CertificationConfigurationError(DecisionCertificationError):
    """Invalid certification configuration."""

class DeterminismValidationError(DecisionCertificationError):
    """Decision determinism validation failed."""

class ReplayValidationError(DecisionCertificationError):
    """Replay validation failed."""

class RegressionValidationError(DecisionCertificationError):
    """Regression validation failed."""

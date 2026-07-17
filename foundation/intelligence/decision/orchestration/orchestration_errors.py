"""Exceptions raised by universal decision orchestration."""


class DecisionOrchestrationError(RuntimeError):
    """Base exception for orchestration failures."""


class OrchestrationInputError(DecisionOrchestrationError):
    """Raised when orchestration inputs are invalid."""


class OrchestrationConfigurationError(DecisionOrchestrationError):
    """Raised when an orchestration profile is invalid."""


class OrchestrationConsistencyError(DecisionOrchestrationError):
    """Raised when intermediate artifacts are inconsistent."""

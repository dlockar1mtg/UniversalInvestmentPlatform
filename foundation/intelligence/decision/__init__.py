"""Universal investment decision intelligence."""

from .classification import (
    ActionClassificationError,
    ActionClassificationResult,
    ClassificationInputError,
    UniversalActionClassificationEngine,
)
from .contracts import (
    DecisionAction,
    DecisionContext,
    DecisionContractError,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    DecisionPolicyError,
    DecisionResult,
    DecisionScore,
    DecisionStatus,
    DecisionValidationError,
    EligibilityStatus,
)
from .eligibility import (
    EligibilityCheck,
    EligibilityResult,
    UniversalEligibilityEngine,
)
from .scoring import (
    DEFAULT_COMPONENT_WEIGHTS,
    DecisionScoringError,
    DecisionScoringProfile,
    IneligibleScoringError,
    ScoringConfigurationError,
    UniversalDecisionScoringEngine,
)

__all__ = [
    "ActionClassificationError",
    "ActionClassificationResult",
    "ClassificationInputError",
    "DEFAULT_COMPONENT_WEIGHTS",
    "DecisionAction",
    "DecisionContext",
    "DecisionContractError",
    "DecisionEvidence",
    "DecisionInput",
    "DecisionPolicy",
    "DecisionPolicyError",
    "DecisionResult",
    "DecisionScore",
    "DecisionScoringError",
    "DecisionScoringProfile",
    "DecisionStatus",
    "DecisionValidationError",
    "EligibilityCheck",
    "EligibilityResult",
    "EligibilityStatus",
    "IneligibleScoringError",
    "ScoringConfigurationError",
    "UniversalActionClassificationEngine",
    "UniversalDecisionScoringEngine",
    "UniversalEligibilityEngine",
]

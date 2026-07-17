"""Complete output of an orchestrated decision evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from ..allocation.allocation_result import AllocationResult
from ..classification.classification_result import (
    ActionClassificationResult,
)
from ..confidence.confidence_result import ConfidenceResult
from ..constraints.constraint_result import ConstraintEvaluationResult
from ..contracts.decision_errors import DecisionValidationError
from ..contracts.decision_result import DecisionResult
from ..eligibility.eligibility_result import EligibilityResult
from ..explanation.explanation_result import DecisionExplanation


@dataclass(frozen=True, slots=True)
class DecisionOrchestrationResult:
    """Final decision plus all intermediate decision artifacts."""

    decision_result: DecisionResult
    eligibility_result: EligibilityResult
    classification_result: ActionClassificationResult
    confidence_result: ConfidenceResult
    constraint_result: ConstraintEvaluationResult
    allocation_result: AllocationResult
    explanation: DecisionExplanation
    engine_version: str = "5.1.8"

    def __post_init__(self) -> None:
        asset_ids = {
            self.decision_result.asset_id,
            self.eligibility_result.asset_id,
            self.classification_result.asset_id,
            self.confidence_result.asset_id,
            self.constraint_result.asset_id,
            self.allocation_result.asset_id,
            self.explanation.asset_id,
        }

        if len(asset_ids) != 1:
            raise DecisionValidationError(
                "All orchestration artifacts must share the same asset_id."
            )

        if not self.engine_version.strip():
            raise DecisionValidationError(
                "engine_version cannot be empty."
            )

    @property
    def decision_id(self) -> str:
        """Return the final decision identifier."""

        return self.decision_result.decision_id

"""Application-service orchestration for universal investment decisions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any, Mapping

from ..allocation.allocation_engine import UniversalAllocationEngine
from ..allocation.allocation_profile import AllocationProfile
from ..classification.classification_engine import (
    UniversalActionClassificationEngine,
)
from ..confidence.confidence_engine import (
    UniversalConfidenceAggregationEngine,
)
from ..confidence.confidence_profile import ConfidenceProfile
from ..constraints.constraint_engine import UniversalConstraintEngine
from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from ..contracts.decision_result import DecisionResult
from ..contracts.decision_score import DecisionScore
from ..contracts.decision_status import (
    DecisionStatus,
    EligibilityStatus,
)
from ..eligibility.eligibility_engine import UniversalEligibilityEngine
from ..explanation.explanation_engine import (
    UniversalDecisionExplanationEngine,
)
from ..explanation.explanation_profile import ExplanationProfile
from ..scoring.scoring_engine import UniversalDecisionScoringEngine
from ..scoring.scoring_profile import DecisionScoringProfile
from .orchestration_errors import OrchestrationInputError
from .orchestration_profile import OrchestrationProfile
from .orchestration_result import DecisionOrchestrationResult


class UniversalDecisionOrchestrator:
    """Coordinate the complete single-opportunity decision workflow."""

    def __init__(
        self,
        *,
        eligibility_engine: UniversalEligibilityEngine | None = None,
        scoring_engine: UniversalDecisionScoringEngine | None = None,
        classification_engine: (
            UniversalActionClassificationEngine | None
        ) = None,
        confidence_engine: (
            UniversalConfidenceAggregationEngine | None
        ) = None,
        constraint_engine: UniversalConstraintEngine | None = None,
        allocation_engine: UniversalAllocationEngine | None = None,
        explanation_engine: (
            UniversalDecisionExplanationEngine | None
        ) = None,
    ) -> None:
        self._eligibility_engine = (
            eligibility_engine or UniversalEligibilityEngine()
        )
        self._scoring_engine = (
            scoring_engine or UniversalDecisionScoringEngine(
                eligibility_engine=self._eligibility_engine
            )
        )
        self._classification_engine = (
            classification_engine
            or UniversalActionClassificationEngine()
        )
        self._confidence_engine = (
            confidence_engine
            or UniversalConfidenceAggregationEngine()
        )
        self._constraint_engine = (
            constraint_engine or UniversalConstraintEngine()
        )
        self._allocation_engine = (
            allocation_engine or UniversalAllocationEngine()
        )
        self._explanation_engine = (
            explanation_engine or UniversalDecisionExplanationEngine()
        )

    def evaluate(
        self,
        decision_input: DecisionInput,
        *,
        requested_allocation: Decimal | None = None,
        decision_policy: DecisionPolicy | None = None,
        scoring_profile: DecisionScoringProfile | None = None,
        confidence_profile: ConfidenceProfile | None = None,
        allocation_profile: AllocationProfile | None = None,
        explanation_profile: ExplanationProfile | None = None,
        orchestration_profile: OrchestrationProfile | None = None,
        generated_at: datetime | None = None,
        decision_id: str | None = None,
    ) -> DecisionOrchestrationResult:
        """Run the complete universal decision pipeline."""

        policy = decision_policy or DecisionPolicy()
        orchestration = (
            orchestration_profile or OrchestrationProfile()
        )

        timestamp = generated_at or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            raise OrchestrationInputError(
                "generated_at must include timezone information."
            )

        eligibility = self._eligibility_engine.evaluate(
            decision_input,
            policy,
        )

        if eligibility.status in {
            EligibilityStatus.ELIGIBLE,
            EligibilityStatus.CONDITIONALLY_ELIGIBLE,
        }:
            score = self._scoring_engine.score(
                decision_input,
                eligibility_result=eligibility,
                decision_policy=policy,
                scoring_profile=scoring_profile,
            )
        else:
            score = self._non_scoring_result(
                eligibility.status
            )

        classification = self._classification_engine.classify(
            decision_input,
            score,
            eligibility,
            policy,
        )

        confidence = self._confidence_engine.aggregate(
            decision_input,
            eligibility,
            decision_policy=policy,
            confidence_profile=confidence_profile,
        )

        constraints = self._constraint_engine.evaluate(
            decision_input,
            classification,
            confidence,
            decision_policy=policy,
        )

        allocation = self._allocation_engine.recommend(
            classification,
            confidence,
            constraints,
            requested_allocation=requested_allocation,
            allocation_profile=allocation_profile,
        )

        explanation = self._explanation_engine.explain(
            decision_input,
            eligibility,
            score,
            classification,
            confidence,
            constraints,
            allocation,
            explanation_profile=explanation_profile,
        )

        final_decision_id = decision_id or self._generate_decision_id(
            decision_input=decision_input,
            generated_at=timestamp,
            policy=policy,
        )

        if not final_decision_id.strip():
            raise OrchestrationInputError(
                "decision_id cannot be empty."
            )

        expires_at = timestamp + timedelta(
            hours=orchestration.expiration_hours
        )

        policy_violations = self._policy_violations(
            eligibility=eligibility,
            constraints=constraints,
        )

        reasons = self._decision_reasons(
            classification_reasons=classification.reasons,
            explanation_summary=explanation.executive_summary,
        )

        metadata = self._build_metadata(
            decision_input=decision_input,
            eligibility=eligibility,
            score=score,
            classification=classification,
            confidence=confidence,
            constraints=constraints,
            allocation=allocation,
            explanation=explanation,
            orchestration=orchestration,
        )

        decision_result = DecisionResult(
            decision_id=final_decision_id,
            asset_id=decision_input.asset_id,
            asset_class=decision_input.asset_class,
            action=classification.action,
            status=DecisionStatus.EVALUATED,
            eligibility=eligibility.status,
            score=score,
            confidence=confidence.final_confidence,
            maximum_allocation=(
                constraints.maximum_permitted_allocation
            ),
            recommended_allocation=(
                allocation.recommended_allocation
            ),
            reasons=reasons,
            evidence=tuple(decision_input.evidence),
            policy_violations=policy_violations,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            generated_at=timestamp,
            expires_at=expires_at,
            metadata=metadata,
        )

        return DecisionOrchestrationResult(
            decision_result=decision_result,
            eligibility_result=eligibility,
            classification_result=classification,
            confidence_result=confidence,
            constraint_result=constraints,
            allocation_result=allocation,
            explanation=explanation,
            engine_version=orchestration.engine_version,
        )

    @staticmethod
    def _non_scoring_result(
        status: EligibilityStatus,
    ) -> DecisionScore:
        """Create a transparent zero score for a non-scoring outcome."""

        return DecisionScore(
            base_score=0.0,
            penalty_score=0.0,
            final_score=0.0,
            component_scores={},
            penalty_components={
                f"eligibility_{status.value}": 0.0
            },
            scoring_version="5.1.8-short-circuit",
        )

    @staticmethod
    def _generate_decision_id(
        *,
        decision_input: DecisionInput,
        generated_at: datetime,
        policy: DecisionPolicy,
    ) -> str:
        """Generate a reproducible decision identifier."""

        source = "|".join(
            (
                decision_input.asset_id,
                decision_input.asset_class,
                decision_input.time_horizon,
                decision_input.context.portfolio_id,
                generated_at.isoformat(),
                policy.policy_id,
                policy.policy_version,
            )
        )

        digest = sha256(source.encode("utf-8")).hexdigest()[:12].upper()

        asset_token = (
            decision_input.asset_id
            .replace(":", "-")
            .replace("/", "-")
            .replace(" ", "-")
            .upper()
        )

        timestamp_token = generated_at.strftime("%Y%m%dT%H%M%SZ")

        return f"DEC-{timestamp_token}-{asset_token}-{digest}"

    @staticmethod
    def _policy_violations(
        *,
        eligibility: Any,
        constraints: Any,
    ) -> tuple[str, ...]:
        violations = [
            check.message
            for check in eligibility.failed_checks
        ]

        violations.extend(
            check.message
            for check in constraints.blocked_checks
        )

        return tuple(dict.fromkeys(violations))

    @staticmethod
    def _decision_reasons(
        *,
        classification_reasons: Any,
        explanation_summary: str,
    ) -> tuple[str, ...]:
        reasons = list(classification_reasons)
        reasons.append(explanation_summary)

        return tuple(dict.fromkeys(reasons))

    @staticmethod
    def _build_metadata(
        *,
        decision_input: DecisionInput,
        eligibility: Any,
        score: DecisionScore,
        classification: Any,
        confidence: Any,
        constraints: Any,
        allocation: Any,
        explanation: Any,
        orchestration: OrchestrationProfile,
    ) -> Mapping[str, Any]:
        metadata: dict[str, Any] = {
            "engine_version": orchestration.engine_version,
            "orchestration_profile_id": orchestration.profile_id,
            "recommended_allocation": str(
                allocation.recommended_allocation
            ),
            "maximum_permitted_allocation": str(
                constraints.maximum_permitted_allocation
            ),
            "binding_constraint": constraints.binding_constraint,
        }

        if orchestration.include_component_versions:
            metadata["component_versions"] = {
                "policy": eligibility.policy_version,
                "scoring": score.scoring_version,
                "classification": (
                    classification.classification_version
                ),
                "confidence": confidence.confidence_version,
                "constraints": constraints.constraint_version,
                "allocation": allocation.allocation_version,
                "explanation": explanation.explanation_version,
            }

        if orchestration.include_explanation_metadata:
            metadata["explanation"] = {
                "headline": explanation.headline,
                "executive_summary": explanation.executive_summary,
                "positive_factors": tuple(
                    explanation.positive_factors
                ),
                "negative_factors": tuple(
                    explanation.negative_factors
                ),
                "warnings": tuple(explanation.warnings),
                "evidence_references": tuple(
                    explanation.evidence_references
                ),
            }

        if orchestration.include_intermediate_artifacts:
            metadata["intermediate_results"] = {
                "eligibility_status": eligibility.status.value,
                "base_score": score.base_score,
                "penalty_score": score.penalty_score,
                "final_score": score.final_score,
                "action": classification.action.value,
                "final_confidence": confidence.final_confidence,
                "confidence_band": (
                    confidence.confidence_band.value
                ),
                "constraint_status": constraints.status.value,
                "allocation_percentage": (
                    allocation.allocation_percentage
                ),
                "audit_facts": dict(explanation.audit_facts),
            }

        metadata["source_metadata"] = dict(
            decision_input.metadata
        )

        return metadata

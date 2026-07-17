"""Fact-based explanations for universal investment decisions."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..allocation.allocation_result import AllocationResult
from ..classification.classification_result import (
    ActionClassificationResult,
)
from ..confidence.confidence_result import ConfidenceResult
from ..constraints.constraint_result import ConstraintEvaluationResult
from ..constraints.constraint_status import ConstraintStatus
from ..contracts.decision_input import DecisionInput
from ..contracts.decision_score import DecisionScore
from ..contracts.decision_status import EligibilityStatus
from ..eligibility.eligibility_result import EligibilityResult
from .explanation_errors import ExplanationInputError
from .explanation_profile import ExplanationProfile
from .explanation_result import DecisionExplanation


class UniversalDecisionExplanationEngine:
    """Create explanations strictly from structured decision artifacts."""

    def explain(
        self,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        decision_score: DecisionScore,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        allocation_result: AllocationResult,
        *,
        explanation_profile: ExplanationProfile | None = None,
    ) -> DecisionExplanation:
        """Produce executive, analytical, and audit explanations."""

        profile = explanation_profile or ExplanationProfile()

        self._validate_inputs(
            decision_input=decision_input,
            eligibility_result=eligibility_result,
            classification_result=classification_result,
            confidence_result=confidence_result,
            constraint_result=constraint_result,
            allocation_result=allocation_result,
        )

        positive_factors = self._positive_factors(
            decision_score=decision_score,
            confidence_result=confidence_result,
            limit=profile.maximum_positive_factors,
        )

        negative_factors = self._negative_factors(
            eligibility_result=eligibility_result,
            decision_score=decision_score,
            confidence_result=confidence_result,
            constraint_result=constraint_result,
            limit=profile.maximum_negative_factors,
        )

        warnings = self._warnings(
            eligibility_result=eligibility_result,
            confidence_result=confidence_result,
            constraint_result=constraint_result,
            allocation_result=allocation_result,
            limit=profile.maximum_warnings,
        )

        evidence_references = tuple(
            evidence.evidence_id
            for evidence in decision_input.evidence[
                : profile.maximum_evidence_references
            ]
        )

        headline = self._headline(
            asset_id=decision_input.asset_id,
            action=classification_result.action.value,
            confidence_band=confidence_result.confidence_band.value,
        )

        executive_summary = self._executive_summary(
            classification_result=classification_result,
            decision_score=decision_score,
            confidence_result=confidence_result,
            allocation_result=allocation_result,
            constraint_result=constraint_result,
        )

        eligibility_explanation = self._eligibility_explanation(
            eligibility_result
        )

        scoring_explanation = self._scoring_explanation(
            decision_score
        )

        confidence_explanation = self._confidence_explanation(
            confidence_result
        )

        constraint_explanation = self._constraint_explanation(
            constraint_result
        )

        allocation_explanation = self._allocation_explanation(
            allocation_result
        )

        audit_facts = (
            self._audit_facts(
                decision_input=decision_input,
                eligibility_result=eligibility_result,
                decision_score=decision_score,
                classification_result=classification_result,
                confidence_result=confidence_result,
                constraint_result=constraint_result,
                allocation_result=allocation_result,
            )
            if profile.include_audit_facts
            else {}
        )

        return DecisionExplanation(
            asset_id=decision_input.asset_id,
            headline=headline,
            executive_summary=executive_summary,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            warnings=warnings,
            eligibility_explanation=eligibility_explanation,
            scoring_explanation=scoring_explanation,
            confidence_explanation=confidence_explanation,
            constraint_explanation=constraint_explanation,
            allocation_explanation=allocation_explanation,
            evidence_references=evidence_references,
            audit_facts=audit_facts,
            explanation_version=profile.explanation_version,
        )

    @staticmethod
    def _validate_inputs(
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        allocation_result: AllocationResult,
    ) -> None:
        asset_ids = {
            decision_input.asset_id,
            eligibility_result.asset_id,
            classification_result.asset_id,
            confidence_result.asset_id,
            constraint_result.asset_id,
            allocation_result.asset_id,
        }

        if len(asset_ids) != 1:
            raise ExplanationInputError(
                "All explanation artifacts must share the same asset_id."
            )

        if classification_result.action is not allocation_result.action:
            raise ExplanationInputError(
                "Classification action and allocation action must match."
            )

        if (
            classification_result.eligibility
            is not eligibility_result.status
        ):
            raise ExplanationInputError(
                "Classification eligibility and EligibilityResult "
                "status must match."
            )

    @staticmethod
    def _positive_factors(
        *,
        decision_score: DecisionScore,
        confidence_result: ConfidenceResult,
        limit: int,
    ) -> tuple[str, ...]:
        if limit == 0:
            return ()

        factors: list[tuple[float, str]] = []

        for name, contribution in decision_score.component_scores.items():
            factors.append(
                (
                    float(contribution),
                    (
                        f"{name.replace('_', ' ').title()} contributed "
                        f"{float(contribution):.2f} weighted points."
                    ),
                )
            )

        factors.append(
            (
                confidence_result.final_confidence * 100.0,
                (
                    f"Recommendation confidence is "
                    f"{confidence_result.final_confidence:.2%} "
                    f"({confidence_result.confidence_band.value.replace('_', ' ')})."
                ),
            )
        )

        factors.sort(key=lambda item: item[0], reverse=True)

        return tuple(text for _, text in factors[:limit])

    @staticmethod
    def _negative_factors(
        *,
        eligibility_result: EligibilityResult,
        decision_score: DecisionScore,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        limit: int,
    ) -> tuple[str, ...]:
        if limit == 0:
            return ()

        factors: list[str] = []

        for name, penalty in sorted(
            decision_score.penalty_components.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            factors.append(
                f"{name.replace('_', ' ').title()} reduced the score "
                f"by {float(penalty):.2f} points."
            )

        for name, adjustment in sorted(
            confidence_result.adjustments.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            factors.append(
                f"{name.replace('_', ' ').title()} reduced confidence "
                f"by {float(adjustment):.2f} points."
            )

        for check in eligibility_result.failed_checks:
            factors.append(check.message)

        for check in constraint_result.blocked_checks:
            factors.append(check.message)

        return tuple(factors[:limit])

    @staticmethod
    def _warnings(
        *,
        eligibility_result: EligibilityResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        allocation_result: AllocationResult,
        limit: int,
    ) -> tuple[str, ...]:
        if limit == 0:
            return ()

        warnings: list[str] = []

        if (
            eligibility_result.status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ):
            warnings.append(
                "The opportunity is only conditionally eligible."
            )

        if confidence_result.final_confidence < 0.55:
            warnings.append(
                "Recommendation confidence is below the moderate band."
            )

        warnings.extend(
            check.message
            for check in constraint_result.warning_checks
        )

        if constraint_result.status is ConstraintStatus.BLOCKED:
            warnings.append(
                "A hard constraint prevents additional allocation."
            )

        if allocation_result.recommended_allocation == 0:
            warnings.append(
                "The recommended additional allocation is zero."
            )

        return tuple(warnings[:limit])

    @staticmethod
    def _headline(
        *,
        asset_id: str,
        action: str,
        confidence_band: str,
    ) -> str:
        return (
            f"{asset_id}: {action.upper()} with "
            f"{confidence_band.replace('_', ' ')} confidence"
        )

    @staticmethod
    def _executive_summary(
        *,
        classification_result: ActionClassificationResult,
        decision_score: DecisionScore,
        confidence_result: ConfidenceResult,
        allocation_result: AllocationResult,
        constraint_result: ConstraintEvaluationResult,
    ) -> str:
        return (
            f"The platform classified this opportunity as "
            f"{classification_result.action.value.upper()} with a final "
            f"decision score of {decision_score.final_score:.2f} and "
            f"confidence of {confidence_result.final_confidence:.2%}. "
            f"The maximum permitted allocation is "
            f"{allocation_result.maximum_allocation:.2f}, and the "
            f"recommended allocation is "
            f"{allocation_result.recommended_allocation:.2f}. "
            f"Constraint status is "
            f"{constraint_result.status.value.upper()}."
        )

    @staticmethod
    def _eligibility_explanation(
        result: EligibilityResult,
    ) -> str:
        failed_count = len(result.failed_checks)

        if failed_count == 0:
            return (
                f"Eligibility status is {result.status.value.upper()}. "
                "All evaluated eligibility and data-quality rules passed."
            )

        return (
            f"Eligibility status is {result.status.value.upper()}. "
            f"{failed_count} eligibility or data-quality check(s) failed."
        )

    @staticmethod
    def _scoring_explanation(
        result: DecisionScore,
    ) -> str:
        return (
            f"The base decision score was {result.base_score:.2f}. "
            f"Explicit penalties totaled {result.penalty_score:.2f}, "
            f"producing a final score of {result.final_score:.2f}. "
            f"Scoring version: {result.scoring_version}."
        )

    @staticmethod
    def _confidence_explanation(
        result: ConfidenceResult,
    ) -> str:
        return (
            f"Raw confidence was {result.raw_confidence:.2%}. "
            f"Adjustments totaled {result.adjustment_score:.2f} points, "
            f"producing final confidence of "
            f"{result.final_confidence:.2%} in the "
            f"{result.confidence_band.value.replace('_', ' ')} band. "
            f"Confidence version: {result.confidence_version}."
        )

    @staticmethod
    def _constraint_explanation(
        result: ConstraintEvaluationResult,
    ) -> str:
        binding = result.binding_constraint or "none"

        return (
            f"Constraint status is {result.status.value.upper()}. "
            f"Maximum permitted allocation is "
            f"{result.maximum_permitted_allocation:.2f}. "
            f"Binding constraint: {binding}. "
            f"Constraint version: {result.constraint_version}."
        )

    @staticmethod
    def _allocation_explanation(
        result: AllocationResult,
    ) -> str:
        return (
            f"Requested allocation was "
            f"{result.requested_allocation:.2f}. "
            f"Recommended allocation is "
            f"{result.recommended_allocation:.2f}, equal to "
            f"{result.allocation_percentage:.2%} of the maximum permitted "
            f"allocation. Allocation version: "
            f"{result.allocation_version}."
        )

    @staticmethod
    def _audit_facts(
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        decision_score: DecisionScore,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        allocation_result: AllocationResult,
    ) -> Mapping[str, Any]:
        return {
            "asset_id": decision_input.asset_id,
            "asset_class": decision_input.asset_class,
            "time_horizon": decision_input.time_horizon,
            "portfolio_id": decision_input.context.portfolio_id,
            "eligibility_status": eligibility_result.status.value,
            "policy_id": eligibility_result.policy_id,
            "policy_version": eligibility_result.policy_version,
            "base_score": decision_score.base_score,
            "penalty_score": decision_score.penalty_score,
            "final_score": decision_score.final_score,
            "scoring_version": decision_score.scoring_version,
            "action": classification_result.action.value,
            "classification_version": (
                classification_result.classification_version
            ),
            "raw_confidence": confidence_result.raw_confidence,
            "final_confidence": confidence_result.final_confidence,
            "confidence_band": confidence_result.confidence_band.value,
            "confidence_version": confidence_result.confidence_version,
            "constraint_status": constraint_result.status.value,
            "maximum_permitted_allocation": str(
                constraint_result.maximum_permitted_allocation
            ),
            "binding_constraint": constraint_result.binding_constraint,
            "constraint_version": constraint_result.constraint_version,
            "requested_allocation": str(
                allocation_result.requested_allocation
            ),
            "recommended_allocation": str(
                allocation_result.recommended_allocation
            ),
            "allocation_version": allocation_result.allocation_version,
            "evidence_count": len(decision_input.evidence),
        }

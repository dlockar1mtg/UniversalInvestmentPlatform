"""Single-decision allocation recommendation engine."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from ..classification.classification_result import (
    ActionClassificationResult,
)
from ..confidence.confidence_result import ConfidenceResult
from ..constraints.constraint_result import ConstraintEvaluationResult
from ..constraints.constraint_status import ConstraintStatus
from ..contracts.decision_action import DecisionAction
from ..contracts.decision_status import EligibilityStatus
from .allocation_errors import AllocationInputError
from .allocation_profile import AllocationProfile
from .allocation_result import AllocationResult


ZERO = Decimal("0")


class UniversalAllocationEngine:
    """Recommend capital for one opportunity within safe limits."""

    def recommend(
        self,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
        *,
        requested_allocation: Decimal | None = None,
        allocation_profile: AllocationProfile | None = None,
    ) -> AllocationResult:
        """Produce a confidence- and action-adjusted allocation."""

        profile = allocation_profile or AllocationProfile()

        self._validate_inputs(
            classification_result=classification_result,
            confidence_result=confidence_result,
            constraint_result=constraint_result,
        )

        maximum = constraint_result.maximum_permitted_allocation

        requested = (
            maximum
            if requested_allocation is None
            else requested_allocation
        )

        if requested < ZERO:
            raise AllocationInputError(
                "requested_allocation cannot be negative."
            )

        requested = min(requested, maximum)

        action_factor = self._action_multiplier(
            classification_result.action,
            profile,
        )

        confidence_factor = max(
            profile.minimum_confidence_multiplier,
            confidence_result.final_confidence,
        )

        eligibility_factor = (
            profile.conditional_eligibility_multiplier
            if classification_result.eligibility
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
            else 1.0
        )

        policy_fraction = profile.maximum_single_decision_fraction

        sizing_factors = {
            "action": action_factor,
            "confidence": confidence_factor,
            "eligibility": eligibility_factor,
            "single_decision_limit": policy_fraction,
        }

        blocked = (
            constraint_result.status is ConstraintStatus.BLOCKED
            or action_factor == 0.0
            or maximum <= ZERO
        )

        if blocked:
            recommended = ZERO
        else:
            combined_factor = (
                action_factor
                * confidence_factor
                * eligibility_factor
                * policy_fraction
            )

            recommended = (
                requested * Decimal(str(combined_factor))
            )

            recommended = min(recommended, maximum)
            recommended = self._round_down(
                recommended,
                profile.rounding_increment,
            )

            minimum = profile.minimum_recommended_allocation

            if ZERO < recommended < minimum:
                recommended = (
                    minimum
                    if minimum <= maximum
                    else ZERO
                )

        allocation_percentage = (
            float(recommended / maximum)
            if maximum > ZERO
            else 0.0
        )

        reasons = self._build_reasons(
            classification=classification_result,
            confidence=confidence_result,
            constraints=constraint_result,
            requested=requested,
            recommended=recommended,
            sizing_factors=sizing_factors,
        )

        return AllocationResult(
            asset_id=classification_result.asset_id,
            action=classification_result.action,
            requested_allocation=requested,
            maximum_allocation=maximum,
            recommended_allocation=recommended,
            allocation_percentage=allocation_percentage,
            binding_constraint=constraint_result.binding_constraint,
            sizing_factors=sizing_factors,
            reasons=reasons,
            allocation_version=profile.allocation_version,
        )

    @staticmethod
    def _validate_inputs(
        *,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        constraint_result: ConstraintEvaluationResult,
    ) -> None:
        asset_ids = {
            classification_result.asset_id,
            confidence_result.asset_id,
            constraint_result.asset_id,
        }

        if len(asset_ids) != 1:
            raise AllocationInputError(
                "Classification, confidence, and constraint "
                "asset identifiers must match."
            )

    @staticmethod
    def _action_multiplier(
        action: DecisionAction,
        profile: AllocationProfile,
    ) -> float:
        return {
            DecisionAction.STRONG_BUY: profile.strong_buy_multiplier,
            DecisionAction.BUY: profile.buy_multiplier,
            DecisionAction.ACCUMULATE: (
                profile.accumulate_multiplier
            ),
            DecisionAction.HOLD: 0.0,
            DecisionAction.WAIT: 0.0,
            DecisionAction.REDUCE: 0.0,
            DecisionAction.SELL: 0.0,
            DecisionAction.AVOID: 0.0,
            DecisionAction.INELIGIBLE: 0.0,
            DecisionAction.INSUFFICIENT_DATA: 0.0,
        }[action]

    @staticmethod
    def _round_down(
        value: Decimal,
        increment: Decimal,
    ) -> Decimal:
        units = (value / increment).to_integral_value(
            rounding=ROUND_DOWN
        )
        return units * increment

    @staticmethod
    def _build_reasons(
        *,
        classification: ActionClassificationResult,
        confidence: ConfidenceResult,
        constraints: ConstraintEvaluationResult,
        requested: Decimal,
        recommended: Decimal,
        sizing_factors: dict[str, float],
    ) -> tuple[str, ...]:
        reasons = [
            (
                f"Action {classification.action.value.upper()} uses an "
                f"action sizing factor of "
                f"{sizing_factors['action']:.2f}."
            ),
            (
                f"Final confidence {confidence.final_confidence:.2%} "
                f"uses a confidence sizing factor of "
                f"{sizing_factors['confidence']:.2f}."
            ),
            (
                f"Requested allocation is {requested:.2f}; "
                f"recommended allocation is {recommended:.2f}."
            ),
        ]

        if constraints.binding_constraint:
            reasons.append(
                "Binding constraint: "
                f"{constraints.binding_constraint}."
            )

        if constraints.status is ConstraintStatus.BLOCKED:
            reasons.append(
                "Allocation is zero because a hard constraint is active."
            )

        return tuple(reasons)

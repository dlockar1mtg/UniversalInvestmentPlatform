"""Universal classification of decision scores into investment actions."""

from __future__ import annotations

from ..contracts.decision_action import DecisionAction
from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from ..contracts.decision_score import DecisionScore
from ..contracts.decision_status import EligibilityStatus
from ..eligibility.eligibility_result import EligibilityResult
from .classification_errors import ClassificationInputError
from .classification_result import ActionClassificationResult


class UniversalActionClassificationEngine:
    """Convert eligibility and final score into a universal action."""

    CLASSIFICATION_VERSION = "5.1.4"

    def classify(
        self,
        decision_input: DecisionInput,
        decision_score: DecisionScore,
        eligibility_result: EligibilityResult,
        policy: DecisionPolicy | None = None,
    ) -> ActionClassificationResult:
        """Assign a universal action and preserve its reasoning."""

        active_policy = policy or DecisionPolicy()

        self._validate_inputs(
            decision_input=decision_input,
            eligibility_result=eligibility_result,
        )

        position_exists = (
            decision_input.context.current_position_value > 0
            or decision_input.context.current_asset_weight > 0
        )

        if eligibility_result.status is EligibilityStatus.INELIGIBLE:
            return ActionClassificationResult(
                asset_id=decision_input.asset_id,
                action=DecisionAction.INELIGIBLE,
                eligibility=eligibility_result.status,
                final_score=decision_score.final_score,
                position_exists=position_exists,
                reasons=tuple(eligibility_result.reasons),
                classification_version=self.CLASSIFICATION_VERSION,
            )

        if (
            eligibility_result.status
            is EligibilityStatus.INSUFFICIENT_DATA
        ):
            return ActionClassificationResult(
                asset_id=decision_input.asset_id,
                action=DecisionAction.INSUFFICIENT_DATA,
                eligibility=eligibility_result.status,
                final_score=decision_score.final_score,
                position_exists=position_exists,
                reasons=tuple(eligibility_result.reasons),
                classification_version=self.CLASSIFICATION_VERSION,
            )

        action = self._classify_score(
            final_score=decision_score.final_score,
            position_exists=position_exists,
            policy=active_policy,
        )

        reasons = [
            self._score_reason(
                final_score=decision_score.final_score,
                action=action,
                position_exists=position_exists,
            )
        ]

        if (
            eligibility_result.status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ):
            adjusted_action = self._apply_conditional_cap(action)

            if adjusted_action is not action:
                reasons.append(
                    "Conditional eligibility caps positive actions at "
                    "ACCUMULATE until the eligibility condition is resolved."
                )
                action = adjusted_action
            else:
                reasons.append(
                    "Conditional eligibility remains attached to the "
                    "classification."
                )

            reasons.extend(eligibility_result.reasons)

        return ActionClassificationResult(
            asset_id=decision_input.asset_id,
            action=action,
            eligibility=eligibility_result.status,
            final_score=decision_score.final_score,
            position_exists=position_exists,
            reasons=tuple(reasons),
            classification_version=self.CLASSIFICATION_VERSION,
        )

    @staticmethod
    def _validate_inputs(
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
    ) -> None:
        if eligibility_result.asset_id != decision_input.asset_id:
            raise ClassificationInputError(
                "EligibilityResult asset_id does not match "
                "DecisionInput asset_id."
            )

    @staticmethod
    def _classify_score(
        *,
        final_score: float,
        position_exists: bool,
        policy: DecisionPolicy,
    ) -> DecisionAction:
        if final_score >= policy.strong_buy_threshold:
            return DecisionAction.STRONG_BUY

        if final_score >= policy.buy_threshold:
            return DecisionAction.BUY

        if final_score >= policy.accumulate_threshold:
            return DecisionAction.ACCUMULATE

        if final_score >= policy.hold_threshold:
            return (
                DecisionAction.HOLD
                if position_exists
                else DecisionAction.WAIT
            )

        if final_score >= policy.reduce_threshold:
            return (
                DecisionAction.REDUCE
                if position_exists
                else DecisionAction.AVOID
            )

        if final_score >= policy.sell_threshold:
            return (
                DecisionAction.SELL
                if position_exists
                else DecisionAction.AVOID
            )

        return (
            DecisionAction.SELL
            if position_exists
            else DecisionAction.AVOID
        )

    @staticmethod
    def _apply_conditional_cap(
        action: DecisionAction,
    ) -> DecisionAction:
        if action in {
            DecisionAction.STRONG_BUY,
            DecisionAction.BUY,
        }:
            return DecisionAction.ACCUMULATE

        return action

    @staticmethod
    def _score_reason(
        *,
        final_score: float,
        action: DecisionAction,
        position_exists: bool,
    ) -> str:
        ownership_text = (
            "an existing position"
            if position_exists
            else "a new opportunity"
        )

        return (
            f"Final decision score {final_score:.2f} classifies "
            f"{ownership_text} as {action.value.upper()}."
        )

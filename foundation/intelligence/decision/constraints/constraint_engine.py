"""Portfolio-aware constraint evaluation for one investment decision."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Iterable

from ..classification.classification_result import (
    ActionClassificationResult,
)
from ..confidence.confidence_result import ConfidenceResult
from ..contracts.decision_action import DecisionAction
from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from .constraint_errors import ConstraintInputError
from .constraint_result import (
    ConstraintCheck,
    ConstraintEvaluationResult,
)
from .constraint_status import ConstraintStatus


ZERO = Decimal("0")
CENT = Decimal("0.01")


class UniversalConstraintEngine:
    """Evaluate hard and soft capital-allocation constraints."""

    def evaluate(
        self,
        decision_input: DecisionInput,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
        *,
        decision_policy: DecisionPolicy | None = None,
    ) -> ConstraintEvaluationResult:
        """Calculate all applicable capital and concentration limits."""

        policy = decision_policy or DecisionPolicy()

        self._validate_inputs(
            decision_input=decision_input,
            classification_result=classification_result,
            confidence_result=confidence_result,
        )

        checks: list[ConstraintCheck] = []

        checks.extend(
            self._evaluate_action_constraints(
                classification_result
            )
        )
        checks.extend(
            self._evaluate_capital_constraints(decision_input)
        )
        checks.extend(
            self._evaluate_concentration_constraints(
                decision_input,
                policy,
            )
        )
        checks.extend(
            self._evaluate_confidence_constraints(
                confidence_result
            )
        )
        checks.extend(
            self._evaluate_execution_constraints(decision_input)
        )

        allocation_limits = [
            check.allocation_limit
            for check in checks
            if check.allocation_limit is not None
        ]

        maximum_allocation = (
            min(allocation_limits)
            if allocation_limits
            else ZERO
        )
        maximum_allocation = max(ZERO, maximum_allocation).quantize(
            CENT,
            rounding=ROUND_DOWN,
        )

        status = self._aggregate_status(checks)

        binding_constraint = self._binding_constraint(
            checks=checks,
            maximum_allocation=maximum_allocation,
        )

        failed_reasons = tuple(
            check.message
            for check in checks
            if check.status is not ConstraintStatus.PASSED
        )

        reasons = failed_reasons or (
            "All active constraints permit additional allocation.",
        )

        return ConstraintEvaluationResult(
            asset_id=decision_input.asset_id,
            status=status,
            checks=tuple(checks),
            maximum_permitted_allocation=maximum_allocation,
            binding_constraint=binding_constraint,
            reasons=reasons,
        )

    @staticmethod
    def _validate_inputs(
        *,
        decision_input: DecisionInput,
        classification_result: ActionClassificationResult,
        confidence_result: ConfidenceResult,
    ) -> None:
        asset_ids = {
            decision_input.asset_id,
            classification_result.asset_id,
            confidence_result.asset_id,
        }

        if len(asset_ids) != 1:
            raise ConstraintInputError(
                "DecisionInput, classification, and confidence "
                "asset identifiers must match."
            )

    @staticmethod
    def _evaluate_action_constraints(
        classification: ActionClassificationResult,
    ) -> Iterable[ConstraintCheck]:
        blocked_actions = {
            DecisionAction.HOLD,
            DecisionAction.WAIT,
            DecisionAction.REDUCE,
            DecisionAction.SELL,
            DecisionAction.AVOID,
            DecisionAction.INELIGIBLE,
            DecisionAction.INSUFFICIENT_DATA,
        }

        blocked = classification.action in blocked_actions

        yield ConstraintCheck(
            constraint_id="action_allocation_permission",
            status=(
                ConstraintStatus.BLOCKED
                if blocked
                else ConstraintStatus.PASSED
            ),
            actual_value=classification.action.value,
            limit_value="capital-increasing action",
            allocation_limit=ZERO if blocked else None,
            message=(
                f"Action {classification.action.value.upper()} does not "
                "permit additional capital allocation."
                if blocked
                else (
                    f"Action {classification.action.value.upper()} "
                    "permits additional capital allocation."
                )
            ),
        )

    @staticmethod
    def _evaluate_capital_constraints(
        decision_input: DecisionInput,
    ) -> Iterable[ConstraintCheck]:
        available = decision_input.context.available_capital
        permitted = max(ZERO, available)

        yield ConstraintCheck(
            constraint_id="available_capital",
            status=(
                ConstraintStatus.PASSED
                if available > ZERO
                else ConstraintStatus.BLOCKED
            ),
            actual_value=available,
            limit_value=available,
            allocation_limit=permitted,
            message=(
                "Available capital is positive."
                if available > ZERO
                else "No positive deployable capital is available."
            ),
        )

    @staticmethod
    def _evaluate_concentration_constraints(
        decision_input: DecisionInput,
        policy: DecisionPolicy,
    ) -> Iterable[ConstraintCheck]:
        context = decision_input.context
        portfolio_value = context.portfolio_value

        if portfolio_value <= ZERO:
            yield ConstraintCheck(
                constraint_id="portfolio_value",
                status=ConstraintStatus.BLOCKED,
                actual_value=portfolio_value,
                limit_value="greater than zero",
                allocation_limit=ZERO,
                message=(
                    "Portfolio value must be positive to calculate "
                    "concentration capacity."
                ),
            )
            return

        maximum_asset_value = (
            portfolio_value
            * Decimal(str(policy.maximum_asset_weight))
        )
        asset_capacity = max(
            ZERO,
            maximum_asset_value - context.current_position_value,
        )

        yield ConstraintCheck(
            constraint_id="asset_weight_capacity",
            status=(
                ConstraintStatus.PASSED
                if asset_capacity > ZERO
                else ConstraintStatus.BLOCKED
            ),
            actual_value=context.current_position_value,
            limit_value=maximum_asset_value,
            allocation_limit=asset_capacity,
            message=(
                "Asset-level concentration capacity remains available."
                if asset_capacity > ZERO
                else "The maximum asset-level allocation has been reached."
            ),
        )

        current_class_value = (
            portfolio_value
            * Decimal(str(context.current_asset_class_weight))
        )
        maximum_class_value = (
            portfolio_value
            * Decimal(str(policy.maximum_asset_class_weight))
        )
        class_capacity = max(
            ZERO,
            maximum_class_value - current_class_value,
        )

        yield ConstraintCheck(
            constraint_id="asset_class_weight_capacity",
            status=(
                ConstraintStatus.PASSED
                if class_capacity > ZERO
                else ConstraintStatus.BLOCKED
            ),
            actual_value=current_class_value,
            limit_value=maximum_class_value,
            allocation_limit=class_capacity,
            message=(
                "Asset-class concentration capacity remains available."
                if class_capacity > ZERO
                else (
                    "The maximum asset-class allocation has been reached."
                )
            ),
        )

        if context.target_asset_weight is not None:
            target_asset_value = (
                portfolio_value
                * Decimal(str(context.target_asset_weight))
            )
            target_gap = max(
                ZERO,
                target_asset_value - context.current_position_value,
            )

            yield ConstraintCheck(
                constraint_id="target_asset_gap",
                status=(
                    ConstraintStatus.PASSED
                    if target_gap > ZERO
                    else ConstraintStatus.WARNING
                ),
                actual_value=context.current_position_value,
                limit_value=target_asset_value,
                allocation_limit=target_gap,
                message=(
                    "The asset remains below its target allocation."
                    if target_gap > ZERO
                    else (
                        "The asset is at or above its target allocation."
                    )
                ),
            )

        if context.target_asset_class_weight is not None:
            target_class_value = (
                portfolio_value
                * Decimal(str(context.target_asset_class_weight))
            )
            target_class_gap = max(
                ZERO,
                target_class_value - current_class_value,
            )

            yield ConstraintCheck(
                constraint_id="target_asset_class_gap",
                status=(
                    ConstraintStatus.PASSED
                    if target_class_gap > ZERO
                    else ConstraintStatus.WARNING
                ),
                actual_value=current_class_value,
                limit_value=target_class_value,
                allocation_limit=target_class_gap,
                message=(
                    "The asset class remains below its target allocation."
                    if target_class_gap > ZERO
                    else (
                        "The asset class is at or above its target "
                        "allocation."
                    )
                ),
            )

    @staticmethod
    def _evaluate_confidence_constraints(
        confidence: ConfidenceResult,
    ) -> Iterable[ConstraintCheck]:
        confidence_factor = Decimal(
            str(confidence.final_confidence)
        )

        status = (
            ConstraintStatus.PASSED
            if confidence.final_confidence >= 0.70
            else ConstraintStatus.WARNING
        )

        yield ConstraintCheck(
            constraint_id="confidence_factor",
            status=status,
            actual_value=confidence.final_confidence,
            limit_value=1.0,
            allocation_limit=None,
            message=(
                "Recommendation confidence supports normal sizing."
                if status is ConstraintStatus.PASSED
                else (
                    "Recommendation confidence requires reduced "
                    "position sizing."
                )
            ),
        )

        # Stored for downstream inspection without independently
        # becoming a hard monetary limit.
        yield ConstraintCheck(
            constraint_id="confidence_multiplier",
            status=status,
            actual_value=confidence_factor,
            limit_value=Decimal("1"),
            allocation_limit=None,
            message=(
                f"Confidence multiplier is "
                f"{confidence.final_confidence:.2%}."
            ),
        )

    @staticmethod
    def _evaluate_execution_constraints(
        decision_input: DecisionInput,
    ) -> Iterable[ConstraintCheck]:
        raw_minimum = decision_input.metadata.get(
            "minimum_transaction_amount",
            0,
        )
        raw_liquidity_limit = decision_input.metadata.get(
            "liquidity_allocation_limit",
            None,
        )
        prohibited = bool(
            decision_input.metadata.get("allocation_prohibited", False)
        )

        try:
            minimum_transaction = Decimal(str(raw_minimum))
        except Exception as exc:
            raise ConstraintInputError(
                "minimum_transaction_amount must be numeric."
            ) from exc

        if minimum_transaction < ZERO:
            raise ConstraintInputError(
                "minimum_transaction_amount cannot be negative."
            )

        yield ConstraintCheck(
            constraint_id="allocation_prohibition",
            status=(
                ConstraintStatus.BLOCKED
                if prohibited
                else ConstraintStatus.PASSED
            ),
            actual_value=prohibited,
            limit_value=False,
            allocation_limit=ZERO if prohibited else None,
            message=(
                "Allocation is prohibited by asset or account policy."
                if prohibited
                else "No explicit allocation prohibition is active."
            ),
        )

        if raw_liquidity_limit is not None:
            try:
                liquidity_limit = Decimal(
                    str(raw_liquidity_limit)
                )
            except Exception as exc:
                raise ConstraintInputError(
                    "liquidity_allocation_limit must be numeric."
                ) from exc

            if liquidity_limit < ZERO:
                raise ConstraintInputError(
                    "liquidity_allocation_limit cannot be negative."
                )

            yield ConstraintCheck(
                constraint_id="liquidity_allocation_limit",
                status=(
                    ConstraintStatus.PASSED
                    if liquidity_limit > ZERO
                    else ConstraintStatus.BLOCKED
                ),
                actual_value=liquidity_limit,
                limit_value=liquidity_limit,
                allocation_limit=liquidity_limit,
                message=(
                    "Liquidity permits a positive allocation."
                    if liquidity_limit > ZERO
                    else "Liquidity does not permit additional allocation."
                ),
            )

        yield ConstraintCheck(
            constraint_id="minimum_transaction_amount",
            status=ConstraintStatus.PASSED,
            actual_value=minimum_transaction,
            limit_value=minimum_transaction,
            allocation_limit=None,
            message=(
                f"Minimum transaction amount is "
                f"{minimum_transaction:.2f}."
            ),
        )

    @staticmethod
    def _aggregate_status(
        checks: Iterable[ConstraintCheck],
    ) -> ConstraintStatus:
        statuses = {check.status for check in checks}

        if ConstraintStatus.BLOCKED in statuses:
            return ConstraintStatus.BLOCKED

        if ConstraintStatus.WARNING in statuses:
            return ConstraintStatus.WARNING

        return ConstraintStatus.PASSED

    @staticmethod
    def _binding_constraint(
        *,
        checks: Iterable[ConstraintCheck],
        maximum_allocation: Decimal,
    ) -> str | None:
        candidates = [
            check
            for check in checks
            if check.allocation_limit is not None
            and check.allocation_limit == maximum_allocation
        ]

        if not candidates:
            return None

        return candidates[0].constraint_id

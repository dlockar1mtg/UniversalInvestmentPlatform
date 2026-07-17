"""Universal eligibility and data-quality evaluation engine."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from ..contracts.decision_status import EligibilityStatus
from .eligibility_check import EligibilityCheck
from .eligibility_result import EligibilityResult


class UniversalEligibilityEngine:
    """Evaluate whether an opportunity may proceed to decision scoring."""

    _STATUS_PRECEDENCE = {
        EligibilityStatus.ELIGIBLE: 0,
        EligibilityStatus.CONDITIONALLY_ELIGIBLE: 1,
        EligibilityStatus.INSUFFICIENT_DATA: 2,
        EligibilityStatus.INELIGIBLE: 3,
    }

    def evaluate(
        self,
        decision_input: DecisionInput,
        policy: DecisionPolicy | None = None,
    ) -> EligibilityResult:
        """Evaluate eligibility, evidence freshness, and portfolio limits."""

        active_policy = policy or DecisionPolicy()
        checks: list[EligibilityCheck] = []

        checks.extend(
            self._evaluate_intelligence_quality(
                decision_input,
                active_policy,
            )
        )
        checks.extend(
            self._evaluate_evidence(
                decision_input,
                active_policy,
            )
        )
        checks.extend(
            self._evaluate_portfolio_constraints(
                decision_input,
                active_policy,
            )
        )

        status = self._aggregate_status(checks)
        reasons = tuple(
            check.message for check in checks if not check.passed
        )

        if not reasons:
            reasons = (
                "Opportunity passes all eligibility and data-quality rules.",
            )

        return EligibilityResult(
            asset_id=decision_input.asset_id,
            status=status,
            checks=tuple(checks),
            reasons=reasons,
            policy_id=active_policy.policy_id,
            policy_version=active_policy.policy_version,
        )

    def _evaluate_intelligence_quality(
        self,
        decision_input: DecisionInput,
        policy: DecisionPolicy,
    ) -> Iterable[EligibilityCheck]:
        yield self._minimum_score_check(
            rule_id="minimum_data_quality",
            actual=decision_input.data_quality,
            minimum=policy.minimum_data_quality,
            tolerance=policy.conditional_shortfall_tolerance,
            severe_failure=EligibilityStatus.INSUFFICIENT_DATA,
            label="Data quality",
        )

        yield self._minimum_score_check(
            rule_id="minimum_forecast_confidence",
            actual=decision_input.forecast_confidence,
            minimum=policy.minimum_forecast_confidence,
            tolerance=policy.conditional_shortfall_tolerance,
            severe_failure=EligibilityStatus.INSUFFICIENT_DATA,
            label="Forecast confidence",
        )

        yield self._minimum_score_check(
            rule_id="minimum_historical_reliability",
            actual=decision_input.historical_reliability,
            minimum=policy.minimum_historical_reliability,
            tolerance=policy.conditional_shortfall_tolerance,
            severe_failure=EligibilityStatus.INSUFFICIENT_DATA,
            label="Historical reliability",
        )

        yield self._minimum_score_check(
            rule_id="minimum_liquidity_quality",
            actual=decision_input.liquidity_quality,
            minimum=policy.minimum_liquidity_quality,
            tolerance=policy.conditional_shortfall_tolerance,
            severe_failure=EligibilityStatus.INELIGIBLE,
            label="Liquidity quality",
        )

    def _evaluate_evidence(
        self,
        decision_input: DecisionInput,
        policy: DecisionPolicy,
    ) -> Iterable[EligibilityCheck]:
        evidence_count = len(decision_input.evidence)

        yield EligibilityCheck(
            rule_id="minimum_evidence_count",
            passed=evidence_count >= policy.minimum_evidence_count,
            actual_value=evidence_count,
            threshold=policy.minimum_evidence_count,
            failure_status=EligibilityStatus.INSUFFICIENT_DATA,
            message=(
                "Evidence count meets the policy minimum."
                if evidence_count >= policy.minimum_evidence_count
                else (
                    f"Evidence count {evidence_count} is below the "
                    f"required minimum of "
                    f"{policy.minimum_evidence_count}."
                )
            ),
        )

        if evidence_count == 0:
            return

        freshness_cutoff = (
            decision_input.context.as_of
            - timedelta(days=policy.maximum_evidence_age_days)
        )

        fresh_count = sum(
            evidence.observed_at >= freshness_cutoff
            for evidence in decision_input.evidence
        )

        if fresh_count == evidence_count:
            yield EligibilityCheck(
                rule_id="evidence_freshness",
                passed=True,
                actual_value=fresh_count,
                threshold=evidence_count,
                message="All evidence records are within the freshness window.",
            )
            return

        if fresh_count == 0:
            yield EligibilityCheck(
                rule_id="evidence_freshness",
                passed=False,
                actual_value=fresh_count,
                threshold=evidence_count,
                failure_status=EligibilityStatus.INSUFFICIENT_DATA,
                message=(
                    "All evidence records are stale under the active policy."
                ),
            )
            return

        yield EligibilityCheck(
            rule_id="evidence_freshness",
            passed=False,
            actual_value=fresh_count,
            threshold=evidence_count,
            failure_status=EligibilityStatus.CONDITIONALLY_ELIGIBLE,
            message=(
                f"Only {fresh_count} of {evidence_count} evidence records "
                "are within the freshness window."
            ),
        )

    def _evaluate_portfolio_constraints(
        self,
        decision_input: DecisionInput,
        policy: DecisionPolicy,
    ) -> Iterable[EligibilityCheck]:
        context = decision_input.context

        capital_passed = (
            policy.allow_negative_available_capital
            or context.available_capital >= 0
        )

        yield EligibilityCheck(
            rule_id="available_capital",
            passed=capital_passed,
            actual_value=context.available_capital,
            threshold=0,
            failure_status=EligibilityStatus.INELIGIBLE,
            message=(
                "Available capital satisfies the active policy."
                if capital_passed
                else (
                    "Available capital is negative and the active policy "
                    "does not permit negative deployable capital."
                )
            ),
        )

        asset_weight_passed = (
            context.current_asset_weight
            <= policy.maximum_asset_weight
        )

        yield EligibilityCheck(
            rule_id="maximum_asset_weight",
            passed=asset_weight_passed,
            actual_value=context.current_asset_weight,
            threshold=policy.maximum_asset_weight,
            failure_status=EligibilityStatus.INELIGIBLE,
            message=(
                "Current asset weight is within the permitted limit."
                if asset_weight_passed
                else (
                    f"Current asset weight "
                    f"{context.current_asset_weight:.2%} exceeds the "
                    f"maximum of {policy.maximum_asset_weight:.2%}."
                )
            ),
        )

        class_weight_passed = (
            context.current_asset_class_weight
            <= policy.maximum_asset_class_weight
        )

        yield EligibilityCheck(
            rule_id="maximum_asset_class_weight",
            passed=class_weight_passed,
            actual_value=context.current_asset_class_weight,
            threshold=policy.maximum_asset_class_weight,
            failure_status=EligibilityStatus.INELIGIBLE,
            message=(
                "Current asset-class weight is within the permitted limit."
                if class_weight_passed
                else (
                    f"Current asset-class weight "
                    f"{context.current_asset_class_weight:.2%} exceeds the "
                    f"maximum of "
                    f"{policy.maximum_asset_class_weight:.2%}."
                )
            ),
        )

    @staticmethod
    def _minimum_score_check(
        *,
        rule_id: str,
        actual: float,
        minimum: float,
        tolerance: float,
        severe_failure: EligibilityStatus,
        label: str,
    ) -> EligibilityCheck:
        if actual >= minimum:
            return EligibilityCheck(
                rule_id=rule_id,
                passed=True,
                actual_value=actual,
                threshold=minimum,
                message=f"{label} meets the policy minimum.",
            )

        shortfall = minimum - actual

        if shortfall <= tolerance:
            failure_status = EligibilityStatus.CONDITIONALLY_ELIGIBLE
            message = (
                f"{label} score {actual:.2f} is below the minimum "
                f"{minimum:.2f}, but remains within the conditional "
                f"tolerance of {tolerance:.2f}."
            )
        else:
            failure_status = severe_failure
            message = (
                f"{label} score {actual:.2f} is materially below the "
                f"required minimum of {minimum:.2f}."
            )

        return EligibilityCheck(
            rule_id=rule_id,
            passed=False,
            actual_value=actual,
            threshold=minimum,
            failure_status=failure_status,
            message=message,
        )

    def _aggregate_status(
        self,
        checks: Iterable[EligibilityCheck],
    ) -> EligibilityStatus:
        failed_statuses = [
            check.failure_status
            for check in checks
            if not check.passed
        ]

        if not failed_statuses:
            return EligibilityStatus.ELIGIBLE

        return max(
            failed_statuses,
            key=self._STATUS_PRECEDENCE.__getitem__,
        )

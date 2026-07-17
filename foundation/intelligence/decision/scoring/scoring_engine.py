"""Transparent weighted scoring for universal investment decisions."""

from __future__ import annotations

from math import isfinite
from typing import Mapping

from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from ..contracts.decision_score import DecisionScore
from ..contracts.decision_status import EligibilityStatus
from ..eligibility.eligibility_engine import UniversalEligibilityEngine
from ..eligibility.eligibility_result import EligibilityResult
from .scoring_errors import (
    DecisionScoringError,
    IneligibleScoringError,
)
from .scoring_profile import DecisionScoringProfile


class UniversalDecisionScoringEngine:
    """Calculate a transparent universal decision score."""

    def __init__(
        self,
        eligibility_engine: UniversalEligibilityEngine | None = None,
    ) -> None:
        self._eligibility_engine = (
            eligibility_engine or UniversalEligibilityEngine()
        )

    def score(
        self,
        decision_input: DecisionInput,
        *,
        eligibility_result: EligibilityResult | None = None,
        decision_policy: DecisionPolicy | None = None,
        scoring_profile: DecisionScoringProfile | None = None,
    ) -> DecisionScore:
        """Calculate weighted components, penalties, and a final score."""

        active_policy = decision_policy or DecisionPolicy()
        active_profile = scoring_profile or DecisionScoringProfile()

        eligibility = eligibility_result or self._eligibility_engine.evaluate(
            decision_input,
            active_policy,
        )

        self._validate_eligibility(
            decision_input=decision_input,
            eligibility_result=eligibility,
        )

        component_values = self._component_values(decision_input)
        weighted_components = {
            name: round(
                component_values[name]
                * active_profile.component_weights[name],
                6,
            )
            for name in active_profile.component_weights
        }

        base_score = round(sum(weighted_components.values()), 6)

        penalties = self._calculate_penalties(
            decision_input=decision_input,
            eligibility_result=eligibility,
            policy=active_policy,
            profile=active_profile,
        )

        penalty_score = round(sum(penalties.values()), 6)
        penalty_score = min(100.0, penalty_score)

        final_score = round(
            max(0.0, min(100.0, base_score - penalty_score)),
            6,
        )

        return DecisionScore(
            base_score=base_score,
            penalty_score=penalty_score,
            final_score=final_score,
            component_scores=weighted_components,
            penalty_components=penalties,
            scoring_version=active_profile.scoring_version,
        )

    @staticmethod
    def _component_values(
        decision_input: DecisionInput,
    ) -> Mapping[str, float]:
        return {
            "forecast_strength": decision_input.forecast_strength,
            "forecast_confidence": decision_input.forecast_confidence,
            "historical_reliability": (
                decision_input.historical_reliability
            ),
            "risk_adjusted_opportunity": (
                decision_input.risk_adjusted_opportunity
            ),
            "market_regime_alignment": (
                decision_input.market_regime_alignment
            ),
            "diversification_fit": decision_input.diversification_fit,
            "liquidity_quality": decision_input.liquidity_quality,
            "valuation_attractiveness": (
                decision_input.valuation_attractiveness
            ),
        }

    @staticmethod
    def _validate_eligibility(
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
    ) -> None:
        if eligibility_result.asset_id != decision_input.asset_id:
            raise DecisionScoringError(
                "Eligibility result asset_id does not match "
                "DecisionInput asset_id."
            )

        if eligibility_result.status in {
            EligibilityStatus.INELIGIBLE,
            EligibilityStatus.INSUFFICIENT_DATA,
        }:
            raise IneligibleScoringError(
                f"Asset {decision_input.asset_id!r} cannot be scored "
                f"because eligibility status is "
                f"{eligibility_result.status.value!r}."
            )

    def _calculate_penalties(
        self,
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        policy: DecisionPolicy,
        profile: DecisionScoringProfile,
    ) -> dict[str, float]:
        penalties: dict[str, float] = {}

        data_penalty = self._data_quality_penalty(
            data_quality=decision_input.data_quality,
            maximum_penalty=profile.maximum_data_quality_penalty,
        )
        if data_penalty > 0:
            penalties["data_quality"] = data_penalty

        if (
            eligibility_result.status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ):
            penalties["conditional_eligibility"] = (
                profile.conditional_eligibility_penalty
            )

        asset_penalty = self._concentration_penalty(
            actual_weight=decision_input.context.current_asset_weight,
            maximum_weight=policy.maximum_asset_weight,
            warning_ratio=profile.concentration_warning_ratio,
            maximum_penalty=(
                profile.maximum_asset_concentration_penalty
            ),
        )
        if asset_penalty > 0:
            penalties["asset_concentration"] = asset_penalty

        class_penalty = self._concentration_penalty(
            actual_weight=(
                decision_input.context.current_asset_class_weight
            ),
            maximum_weight=policy.maximum_asset_class_weight,
            warning_ratio=profile.concentration_warning_ratio,
            maximum_penalty=(
                profile.maximum_asset_class_concentration_penalty
            ),
        )
        if class_penalty > 0:
            penalties["asset_class_concentration"] = class_penalty

        freshness_failed = any(
            check.rule_id == "evidence_freshness"
            and not check.passed
            and check.failure_status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
            for check in eligibility_result.checks
        )

        if freshness_failed:
            penalties["partial_evidence_freshness"] = (
                profile.partial_evidence_freshness_penalty
            )

        conflict_penalty = self._evidence_conflict_penalty(
            decision_input=decision_input,
            maximum_penalty=(
                profile.maximum_evidence_conflict_penalty
            ),
        )
        if conflict_penalty > 0:
            penalties["evidence_conflict"] = conflict_penalty

        return {
            name: round(value, 6)
            for name, value in penalties.items()
            if value > 0
        }

    @staticmethod
    def _data_quality_penalty(
        *,
        data_quality: float,
        maximum_penalty: float,
    ) -> float:
        deficiency_ratio = (100.0 - data_quality) / 100.0
        return max(0.0, deficiency_ratio * maximum_penalty)

    @staticmethod
    def _concentration_penalty(
        *,
        actual_weight: float,
        maximum_weight: float,
        warning_ratio: float,
        maximum_penalty: float,
    ) -> float:
        if maximum_weight <= 0:
            return maximum_penalty if actual_weight > 0 else 0.0

        warning_weight = maximum_weight * warning_ratio

        if actual_weight <= warning_weight:
            return 0.0

        available_range = maximum_weight - warning_weight

        if available_range <= 0:
            return maximum_penalty

        exposure_ratio = (
            actual_weight - warning_weight
        ) / available_range

        return min(
            maximum_penalty,
            max(0.0, exposure_ratio * maximum_penalty),
        )

    @staticmethod
    def _evidence_conflict_penalty(
        *,
        decision_input: DecisionInput,
        maximum_penalty: float,
    ) -> float:
        raw_conflict = decision_input.metadata.get(
            "evidence_conflict_score",
            0.0,
        )

        try:
            conflict_score = float(raw_conflict)
        except (TypeError, ValueError) as exc:
            raise DecisionScoringError(
                "metadata['evidence_conflict_score'] must be numeric."
            ) from exc

        if not isfinite(conflict_score):
            raise DecisionScoringError(
                "metadata['evidence_conflict_score'] must be finite."
            )

        if not 0.0 <= conflict_score <= 100.0:
            raise DecisionScoringError(
                "metadata['evidence_conflict_score'] must be "
                "between 0.0 and 100.0."
            )

        return (conflict_score / 100.0) * maximum_penalty

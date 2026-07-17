"""Universal aggregation of recommendation confidence."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from ..contracts.decision_input import DecisionInput
from ..contracts.decision_policy import DecisionPolicy
from ..contracts.decision_status import EligibilityStatus
from ..eligibility.eligibility_result import EligibilityResult
from .confidence_band import ConfidenceBand
from .confidence_errors import ConfidenceInputError
from .confidence_profile import ConfidenceProfile
from .confidence_result import ConfidenceResult


class UniversalConfidenceAggregationEngine:
    """Calculate confidence independently from opportunity score."""

    def aggregate(
        self,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        *,
        decision_policy: DecisionPolicy | None = None,
        confidence_profile: ConfidenceProfile | None = None,
    ) -> ConfidenceResult:
        """Aggregate components and explicit confidence adjustments."""

        active_policy = decision_policy or DecisionPolicy()
        active_profile = confidence_profile or ConfidenceProfile()

        self._validate_inputs(
            decision_input=decision_input,
            eligibility_result=eligibility_result,
        )

        components = self._component_values(
            decision_input=decision_input,
            eligibility_result=eligibility_result,
        )

        weighted_components = {
            name: round(
                components[name]
                * active_profile.component_weights[name],
                6,
            )
            for name in active_profile.component_weights
        }

        raw_score = round(sum(weighted_components.values()), 6)
        raw_confidence = round(raw_score / 100.0, 6)

        adjustments = self._calculate_adjustments(
            decision_input=decision_input,
            eligibility_result=eligibility_result,
            policy=active_policy,
            profile=active_profile,
        )

        adjustment_score = round(
            min(100.0, sum(adjustments.values())),
            6,
        )

        final_confidence = round(
            max(
                0.0,
                min(
                    1.0,
                    (raw_score - adjustment_score) / 100.0,
                ),
            ),
            6,
        )

        band = self._classify_band(
            confidence=final_confidence,
            profile=active_profile,
        )

        reasons = self._build_reasons(
            raw_confidence=raw_confidence,
            final_confidence=final_confidence,
            band=band,
            components=components,
            adjustments=adjustments,
        )

        return ConfidenceResult(
            asset_id=decision_input.asset_id,
            raw_confidence=raw_confidence,
            adjustment_score=adjustment_score,
            final_confidence=final_confidence,
            confidence_band=band,
            component_scores=weighted_components,
            adjustments=adjustments,
            reasons=reasons,
            confidence_version=active_profile.confidence_version,
        )

    @staticmethod
    def _validate_inputs(
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
    ) -> None:
        if eligibility_result.asset_id != decision_input.asset_id:
            raise ConfidenceInputError(
                "EligibilityResult asset_id does not match "
                "DecisionInput asset_id."
            )

    def _component_values(
        self,
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
    ) -> Mapping[str, float]:
        return {
            "forecast_confidence": decision_input.forecast_confidence,
            "historical_reliability": (
                decision_input.historical_reliability
            ),
            "data_quality": decision_input.data_quality,
            "evidence_quality": self._evidence_quality(decision_input),
            "evidence_consistency": self._evidence_consistency(
                decision_input
            ),
            "eligibility_quality": self._eligibility_quality(
                eligibility_result.status
            ),
        }

    @staticmethod
    def _evidence_quality(
        decision_input: DecisionInput,
    ) -> float:
        if not decision_input.evidence:
            return 0.0

        return (
            sum(
                float(evidence.weight) * 100.0
                for evidence in decision_input.evidence
            )
            / len(decision_input.evidence)
        )

    def _evidence_consistency(
        self,
        decision_input: DecisionInput,
    ) -> float:
        conflict_score = self._metadata_score(
            decision_input.metadata,
            "evidence_conflict_score",
        )

        return 100.0 - conflict_score

    @staticmethod
    def _eligibility_quality(
        status: EligibilityStatus,
    ) -> float:
        return {
            EligibilityStatus.ELIGIBLE: 100.0,
            EligibilityStatus.CONDITIONALLY_ELIGIBLE: 70.0,
            EligibilityStatus.INSUFFICIENT_DATA: 35.0,
            EligibilityStatus.INELIGIBLE: 20.0,
        }[status]

    def _calculate_adjustments(
        self,
        *,
        decision_input: DecisionInput,
        eligibility_result: EligibilityResult,
        policy: DecisionPolicy,
        profile: ConfidenceProfile,
    ) -> dict[str, float]:
        adjustments: dict[str, float] = {}

        if (
            eligibility_result.status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ):
            adjustments["conditional_eligibility"] = (
                profile.conditional_eligibility_adjustment
            )

        partial_freshness = any(
            check.rule_id == "evidence_freshness"
            and not check.passed
            and check.failure_status
            is EligibilityStatus.CONDITIONALLY_ELIGIBLE
            for check in eligibility_result.checks
        )

        if partial_freshness:
            adjustments["partial_evidence_freshness"] = (
                profile.partial_evidence_freshness_adjustment
            )

        evidence_count = len(decision_input.evidence)

        if evidence_count < policy.minimum_evidence_count:
            required = max(1, policy.minimum_evidence_count)
            missing_ratio = (
                policy.minimum_evidence_count - evidence_count
            ) / required

            adjustments["limited_evidence"] = min(
                profile.maximum_limited_evidence_adjustment,
                missing_ratio
                * profile.maximum_limited_evidence_adjustment,
            )

        model_disagreement = self._metadata_score(
            decision_input.metadata,
            "forecast_model_disagreement",
        )
        if model_disagreement > 0:
            adjustments["model_disagreement"] = (
                model_disagreement
                / 100.0
                * profile.maximum_model_disagreement_adjustment
            )

        unsupported_assumptions = self._metadata_score(
            decision_input.metadata,
            "unsupported_assumption_score",
        )
        if unsupported_assumptions > 0:
            adjustments["unsupported_assumptions"] = (
                unsupported_assumptions
                / 100.0
                * profile.maximum_unsupported_assumption_adjustment
            )

        regime_instability = self._metadata_score(
            decision_input.metadata,
            "regime_instability_score",
        )
        if regime_instability > 0:
            adjustments["regime_instability"] = (
                regime_instability
                / 100.0
                * profile.maximum_regime_instability_adjustment
            )

        return {
            name: round(value, 6)
            for name, value in adjustments.items()
            if value > 0
        }

    @staticmethod
    def _metadata_score(
        metadata: Mapping[str, Any],
        key: str,
    ) -> float:
        raw_value = metadata.get(key, 0.0)

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ConfidenceInputError(
                f"metadata[{key!r}] must be numeric."
            ) from exc

        if not isfinite(value):
            raise ConfidenceInputError(
                f"metadata[{key!r}] must be finite."
            )

        if not 0.0 <= value <= 100.0:
            raise ConfidenceInputError(
                f"metadata[{key!r}] must be between 0.0 and 100.0."
            )

        return value

    @staticmethod
    def _classify_band(
        *,
        confidence: float,
        profile: ConfidenceProfile,
    ) -> ConfidenceBand:
        if confidence >= profile.very_high_threshold:
            return ConfidenceBand.VERY_HIGH

        if confidence >= profile.high_threshold:
            return ConfidenceBand.HIGH

        if confidence >= profile.moderate_threshold:
            return ConfidenceBand.MODERATE

        if confidence >= profile.low_threshold:
            return ConfidenceBand.LOW

        return ConfidenceBand.VERY_LOW

    @staticmethod
    def _build_reasons(
        *,
        raw_confidence: float,
        final_confidence: float,
        band: ConfidenceBand,
        components: Mapping[str, float],
        adjustments: Mapping[str, float],
    ) -> tuple[str, ...]:
        strongest_component = max(
            components,
            key=components.__getitem__,
        )
        weakest_component = min(
            components,
            key=components.__getitem__,
        )

        reasons = [
            (
                f"Raw confidence is {raw_confidence:.2%}; "
                f"final confidence is {final_confidence:.2%} "
                f"({band.value.replace('_', ' ')})."
            ),
            (
                f"Strongest confidence component is "
                f"{strongest_component.replace('_', ' ')} "
                f"at {components[strongest_component]:.2f}."
            ),
            (
                f"Weakest confidence component is "
                f"{weakest_component.replace('_', ' ')} "
                f"at {components[weakest_component]:.2f}."
            ),
        ]

        if adjustments:
            reasons.append(
                "Confidence adjustments applied: "
                + ", ".join(
                    f"{name.replace('_', ' ')}={value:.2f}"
                    for name, value in adjustments.items()
                )
                + "."
            )
        else:
            reasons.append(
                "No confidence adjustments were required."
            )

        return tuple(reasons)


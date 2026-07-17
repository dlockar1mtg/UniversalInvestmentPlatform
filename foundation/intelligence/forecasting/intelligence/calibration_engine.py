"""Adaptive confidence calibration engine."""

from __future__ import annotations

from collections.abc import Iterable

from .calibration_contracts import (
    CalibrationStrength,
    ConfidenceCalibrationEvidence,
    ConfidenceCalibrationProfile,
    ConfidenceCalibrationRequest,
    ConfidenceCalibrationResult,
    MarketRegime,
)


class AdaptiveConfidenceCalibrationEngine:
    """Calibrate model confidence using historical reliability evidence."""

    def __init__(
        self,
        profile: ConfidenceCalibrationProfile | None = None,
    ) -> None:
        self.profile = profile or ConfidenceCalibrationProfile()

    def calibrate(
        self,
        request: ConfidenceCalibrationRequest,
        evidence_records: Iterable[ConfidenceCalibrationEvidence],
    ) -> ConfidenceCalibrationResult:
        compatible = tuple(
            evidence
            for evidence in evidence_records
            if evidence.model_key
            == (request.engine_name, request.engine_version)
            and evidence.asset_class == request.asset_class
            and evidence.horizon is request.horizon
            and evidence.evaluation_date <= request.as_of_date
        )

        selected = self._select_evidence(request, compatible)

        if selected is None:
            adjustment = -self.profile.maximum_negative_adjustment
            calibrated = max(0.0, request.raw_confidence + adjustment)
            return ConfidenceCalibrationResult(
                raw_confidence=request.raw_confidence,
                calibrated_confidence=calibrated,
                adjustment=calibrated - request.raw_confidence,
                reliability_score=0.0,
                sample_factor=0.0,
                freshness_factor=0.0,
                regime_match_score=0.0,
                evidence_count=len(compatible),
                strength=CalibrationStrength.INSUFFICIENT,
                selected_evidence=None,
                explanation=(
                    "No compatible calibration evidence was available.",
                    "Confidence was reduced using the maximum evidence penalty.",
                ),
            )

        sample_factor = min(
            1.0,
            selected.sample_size / self.profile.target_sample_size,
        )
        age_days = (
            request.as_of_date - selected.evaluation_date
        ).days
        freshness_factor = max(
            0.0,
            1.0 - age_days / self.profile.stale_after_days,
        )
        regime_match = self._regime_match_score(
            request.regime,
            selected.regime,
        )
        reliability_score = self._reliability_score(selected)

        combined_score = (
            request.consensus_score * self.profile.consensus_weight
            + reliability_score * self.profile.reliability_weight
            + regime_match * self.profile.regime_match_weight
            + freshness_factor * self.profile.freshness_weight
        )
        combined_score *= sample_factor

        # Apply a directional correction for historical overconfidence or
        # underconfidence. A model whose empirical success rate is materially
        # below its reported confidence must not receive a positive adjustment
        # simply because its evidence is fresh or regime-matched.
        reliability_gap_correction = selected.reliability_gap * 0.25
        calibration_signal = min(
            1.0,
            max(0.0, combined_score + reliability_gap_correction),
        )

        centered = calibration_signal - 0.50
        if centered >= 0:
            requested_adjustment = (
                centered
                / 0.50
                * self.profile.maximum_positive_adjustment
            )
        else:
            requested_adjustment = (
                centered
                / 0.50
                * self.profile.maximum_negative_adjustment
            )

        quality_modifier = 0.50 + 0.50 * request.model_quality_score
        requested_adjustment *= quality_modifier

        calibrated = min(
            1.0,
            max(0.0, request.raw_confidence + requested_adjustment),
        )
        adjustment = calibrated - request.raw_confidence
        strength = self._strength(
            reliability_score=reliability_score,
            sample_factor=sample_factor,
            freshness_factor=freshness_factor,
            regime_match=regime_match,
        )

        explanation = self._build_explanation(
            request=request,
            selected=selected,
            adjustment=adjustment,
            reliability_score=reliability_score,
            sample_factor=sample_factor,
            freshness_factor=freshness_factor,
            regime_match=regime_match,
            strength=strength,
        )

        return ConfidenceCalibrationResult(
            raw_confidence=request.raw_confidence,
            calibrated_confidence=calibrated,
            adjustment=adjustment,
            reliability_score=reliability_score,
            sample_factor=sample_factor,
            freshness_factor=freshness_factor,
            regime_match_score=regime_match,
            evidence_count=len(compatible),
            strength=strength,
            selected_evidence=selected,
            explanation=explanation,
            metrics={
                "combined_score": combined_score,
                "reliability_gap_correction": reliability_gap_correction,
                "calibration_signal": calibration_signal,
                "historical_reliability_gap": selected.reliability_gap,
                "calibration_error": selected.calibration_error,
                "interval_coverage": selected.interval_coverage,
            },
        )

    @staticmethod
    def _select_evidence(
        request: ConfidenceCalibrationRequest,
        compatible: tuple[ConfidenceCalibrationEvidence, ...],
    ) -> ConfidenceCalibrationEvidence | None:
        if not compatible:
            return None

        def sort_key(
            evidence: ConfidenceCalibrationEvidence,
        ) -> tuple[object, ...]:
            exact_regime = evidence.regime is request.regime
            unknown_regime = evidence.regime is MarketRegime.UNKNOWN
            regime_rank = 0 if exact_regime else 1 if unknown_regime else 2
            return (
                regime_rank,
                -evidence.evaluation_date.toordinal(),
                -evidence.sample_size,
            )

        return min(compatible, key=sort_key)

    @staticmethod
    def _regime_match_score(
        requested: MarketRegime,
        evidence: MarketRegime,
    ) -> float:
        if evidence is requested:
            return 1.0
        if evidence is MarketRegime.UNKNOWN:
            return 0.60
        if requested is MarketRegime.UNKNOWN:
            return 0.50
        return 0.20

    @staticmethod
    def _reliability_score(
        evidence: ConfidenceCalibrationEvidence,
    ) -> float:
        gap_score = max(
            0.0,
            1.0 - abs(evidence.reliability_gap),
        )
        calibration_score = 1.0 - evidence.calibration_error
        coverage_score = evidence.interval_coverage
        return (
            gap_score * 0.45
            + calibration_score * 0.35
            + coverage_score * 0.20
        )

    @staticmethod
    def _strength(
        *,
        reliability_score: float,
        sample_factor: float,
        freshness_factor: float,
        regime_match: float,
    ) -> CalibrationStrength:
        support = min(
            reliability_score,
            sample_factor,
            freshness_factor,
            regime_match,
        )
        if support >= 0.85:
            return CalibrationStrength.VERY_STRONG
        if support >= 0.70:
            return CalibrationStrength.STRONG
        if support >= 0.50:
            return CalibrationStrength.MODERATE
        if support > 0.0:
            return CalibrationStrength.WEAK
        return CalibrationStrength.INSUFFICIENT

    @staticmethod
    def _build_explanation(
        *,
        request: ConfidenceCalibrationRequest,
        selected: ConfidenceCalibrationEvidence,
        adjustment: float,
        reliability_score: float,
        sample_factor: float,
        freshness_factor: float,
        regime_match: float,
        strength: CalibrationStrength,
    ) -> tuple[str, ...]:
        direction = (
            "increased"
            if adjustment > 0
            else "decreased"
            if adjustment < 0
            else "left unchanged"
        )
        return (
            (
                f"Confidence was {direction} by "
                f"{abs(adjustment):.3f}."
            ),
            (
                f"Historical reliability score was "
                f"{reliability_score:.3f}."
            ),
            (
                f"Evidence support: sample={sample_factor:.3f}, "
                f"freshness={freshness_factor:.3f}, "
                f"regime match={regime_match:.3f}."
            ),
            (
                f"Calibration strength was "
                f"{strength.value.replace('_', ' ')} using "
                f"{selected.regime.value} evidence."
            ),
            (
                f"Consensus input was {request.consensus_score:.3f} and "
                f"model quality was {request.model_quality_score:.3f}."
            ),
        )

"""Forecast quality scoring engine."""

from __future__ import annotations

from datetime import date

from .quality_contracts import (
    ForecastModelEvidence,
    ForecastQualityGrade,
    ForecastQualityProfile,
    ForecastQualityScore,
)


class ForecastQualityEngine:
    """Convert historical evidence into a comparable quality score."""

    def __init__(
        self,
        profile: ForecastQualityProfile | None = None,
    ) -> None:
        self.profile = profile or ForecastQualityProfile()

    def score(
        self,
        evidence: ForecastModelEvidence,
        *,
        as_of_date: date | None = None,
    ) -> ForecastQualityScore:
        """Calculate weighted quality with sample, freshness, and bias effects."""

        reference_date = as_of_date or evidence.evaluation_date
        if evidence.evaluation_date > reference_date:
            raise ValueError(
                "evaluation_date cannot be after the scoring as_of_date."
            )

        components = {
            "accuracy": evidence.accuracy_score,
            "calibration": evidence.calibration_score,
            "directional": evidence.directional_accuracy,
            "stability": evidence.stability_score,
            "coverage": evidence.coverage_score,
        }
        raw_score = (
            evidence.accuracy_score * self.profile.accuracy_weight
            + evidence.calibration_score * self.profile.calibration_weight
            + evidence.directional_accuracy
            * self.profile.directional_weight
            + evidence.stability_score * self.profile.stability_weight
            + evidence.coverage_score * self.profile.coverage_weight
        )

        sample_factor = min(
            1.0,
            evidence.sample_size / self.profile.target_sample_size,
        )
        age_days = (reference_date - evidence.evaluation_date).days
        freshness_factor = max(
            0.0,
            1.0 - age_days / self.profile.stale_after_days,
        )
        bias_penalty = min(1.0, abs(evidence.bias_score))
        adjusted_score = max(
            0.0,
            min(
                1.0,
                raw_score
                * sample_factor
                * freshness_factor
                * (1.0 - bias_penalty),
            ),
        )

        reasons: list[str] = []
        if evidence.sample_size < self.profile.minimum_sample_size:
            reasons.append(
                "Insufficient historical sample size."
            )
        if freshness_factor == 0.0:
            reasons.append("Historical evidence is stale.")
        if bias_penalty >= 0.25:
            reasons.append("Material forecast bias detected.")
        if adjusted_score < self.profile.minimum_eligible_score:
            reasons.append("Adjusted quality is below eligibility threshold.")

        eligible = (
            evidence.sample_size >= self.profile.minimum_sample_size
            and freshness_factor > 0.0
            and adjusted_score >= self.profile.minimum_eligible_score
        )

        return ForecastQualityScore(
            evidence=evidence,
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            sample_factor=sample_factor,
            freshness_factor=freshness_factor,
            bias_penalty=bias_penalty,
            eligible=eligible,
            grade=self._grade(adjusted_score, eligible),
            reasons=tuple(reasons),
            component_scores=components,
        )

    @staticmethod
    def _grade(
        adjusted_score: float,
        eligible: bool,
    ) -> ForecastQualityGrade:
        if not eligible:
            return ForecastQualityGrade.INSUFFICIENT
        if adjusted_score >= 0.85:
            return ForecastQualityGrade.EXCELLENT
        if adjusted_score >= 0.70:
            return ForecastQualityGrade.STRONG
        if adjusted_score >= 0.50:
            return ForecastQualityGrade.ACCEPTABLE
        return ForecastQualityGrade.WEAK

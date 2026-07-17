"""Tests for Phase 4.2.3 adaptive confidence calibration."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.intelligence import (
    AdaptiveConfidenceCalibrationEngine,
    CalibrationStrength,
    ConfidenceCalibrationEvidence,
    ConfidenceCalibrationProfile,
    ConfidenceCalibrationRequest,
    ForecastConfidenceCalibrationService,
    ForecastModelEvidence,
    ForecastQualityEngine,
    MarketRegime,
)
from foundation.intelligence.forecasting.intelligence.consensus_contracts import (
    ConsensusStrength,
    ForecastConsensusResult,
)
from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)


def evidence(
    *,
    regime: MarketRegime = MarketRegime.BULL,
    evaluation_date: date = date(2026, 7, 17),
    sample_size: int = 250,
    reported: float = 0.70,
    empirical: float = 0.78,
    error: float = 0.08,
    coverage: float = 0.82,
) -> ConfidenceCalibrationEvidence:
    return ConfidenceCalibrationEvidence(
        engine_name="model-a",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        regime=regime,
        evaluation_date=evaluation_date,
        sample_size=sample_size,
        mean_reported_confidence=reported,
        empirical_success_rate=empirical,
        calibration_error=error,
        interval_coverage=coverage,
    )


def request(
    *,
    regime: MarketRegime = MarketRegime.BULL,
    raw_confidence: float = 0.70,
    consensus: float = 0.90,
    quality: float = 0.85,
) -> ConfidenceCalibrationRequest:
    return ConfidenceCalibrationRequest(
        engine_name="model-a",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        regime=regime,
        as_of_date=date(2026, 7, 17),
        raw_confidence=raw_confidence,
        consensus_score=consensus,
        model_quality_score=quality,
    )


def universal_forecast() -> UniversalForecast:
    return UniversalForecast(
        asset_id="BTC-USD",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100_000.0,
        point_forecast=115_000.0,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="model-a",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        confidence_score=0.70,
        expected_return=0.15,
    )


def quality_score():
    item = ForecastModelEvidence(
        engine_name="model-a",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=250,
        accuracy_score=0.85,
        calibration_score=0.85,
        directional_accuracy=0.85,
        stability_score=0.85,
        coverage_score=0.85,
    )
    return ForecastQualityEngine().score(item)


def consensus_result() -> ForecastConsensusResult:
    return ForecastConsensusResult(
        asset_id="BTC-USD",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        model_count=3,
        consensus_value=114_000.0,
        consensus_direction=ForecastDirection.UP,
        value_agreement_score=0.90,
        direction_agreement_score=1.0,
        quality_agreement_score=0.90,
        consensus_score=0.93,
        strength=ConsensusStrength.VERY_STRONG,
        dispersion_ratio=0.03,
        confidence_adjustment=0.10,
    )


def test_profile_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        ConfidenceCalibrationProfile(consensus_weight=0.50)


def test_evidence_reliability_gap_is_calculated() -> None:
    item = evidence(reported=0.70, empirical=0.80)

    assert item.reliability_gap == pytest.approx(0.10)


def test_strong_reliability_can_increase_confidence() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (evidence(),),
    )

    assert result.calibrated_confidence > result.raw_confidence
    assert result.adjustment > 0
    assert result.selected_evidence is not None


def test_poor_reliability_reduces_confidence() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(consensus=0.20, quality=0.30),
        (
            evidence(
                reported=0.90,
                empirical=0.40,
                error=0.45,
                coverage=0.40,
            ),
        ),
    )

    assert result.calibrated_confidence < result.raw_confidence
    assert result.adjustment < 0


def test_no_evidence_applies_insufficient_penalty() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (),
    )

    assert result.strength is CalibrationStrength.INSUFFICIENT
    assert result.selected_evidence is None
    assert result.calibrated_confidence < result.raw_confidence


def test_exact_regime_evidence_is_preferred() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(regime=MarketRegime.BEAR),
        (
            evidence(
                regime=MarketRegime.UNKNOWN,
                evaluation_date=date(2026, 7, 17),
            ),
            evidence(
                regime=MarketRegime.BEAR,
                evaluation_date=date(2026, 7, 1),
            ),
        ),
    )

    assert result.selected_evidence is not None
    assert result.selected_evidence.regime is MarketRegime.BEAR
    assert result.regime_match_score == 1.0


def test_unknown_regime_evidence_is_valid_fallback() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(regime=MarketRegime.BEAR),
        (evidence(regime=MarketRegime.UNKNOWN),),
    )

    assert result.regime_match_score == pytest.approx(0.60)


def test_stale_evidence_loses_freshness() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (
            evidence(
                evaluation_date=date(2025, 1, 1),
            ),
        ),
    )

    assert result.freshness_factor == 0.0
    assert result.strength in (
        CalibrationStrength.WEAK,
        CalibrationStrength.INSUFFICIENT,
    )


def test_small_sample_reduces_support() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (evidence(sample_size=25),),
    )

    assert result.sample_factor == pytest.approx(0.10)
    assert result.strength is CalibrationStrength.WEAK


def test_adjustment_is_bounded_at_one() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(raw_confidence=0.98),
        (evidence(),),
    )

    assert result.calibrated_confidence <= 1.0


def test_future_evidence_is_ignored() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (
            evidence(
                evaluation_date=date(2026, 7, 18),
            ),
        ),
    )

    assert result.selected_evidence is None


def test_service_updates_forecast_confidence_and_metadata() -> None:
    updated, result = (
        ForecastConfidenceCalibrationService().calibrate_forecast(
            universal_forecast(),
            asset_class="crypto",
            regime=MarketRegime.BULL,
            quality_score=quality_score(),
            consensus_result=consensus_result(),
            evidence_records=(evidence(),),
        )
    )

    assert updated.confidence_score == pytest.approx(
        result.calibrated_confidence
    )
    assert updated.metadata["confidence_calibration"]["strength"] == (
        result.strength.value
    )
    assert len(updated.notes) == len(result.explanation)


def test_service_requires_raw_confidence() -> None:
    forecast = universal_forecast()
    forecast = UniversalForecast(
        asset_id=forecast.asset_id,
        as_of_date=forecast.as_of_date,
        target_date=forecast.target_date,
        horizon=forecast.horizon,
        reference_value=forecast.reference_value,
        point_forecast=forecast.point_forecast,
        currency=forecast.currency,
        provenance=forecast.provenance,
        direction=forecast.direction,
        expected_return=forecast.expected_return,
    )

    with pytest.raises(ValueError, match="must include confidence_score"):
        ForecastConfidenceCalibrationService().calibrate_forecast(
            forecast,
            asset_class="crypto",
            regime=MarketRegime.BULL,
            quality_score=quality_score(),
            consensus_result=consensus_result(),
            evidence_records=(evidence(),),
        )


def test_service_rejects_mismatched_quality_model() -> None:
    mismatched = ForecastModelEvidence(
        engine_name="other-model",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=250,
        accuracy_score=0.85,
        calibration_score=0.85,
        directional_accuracy=0.85,
        stability_score=0.85,
        coverage_score=0.85,
    )

    with pytest.raises(ValueError, match="does not match forecast"):
        ForecastConfidenceCalibrationService().calibrate_forecast(
            universal_forecast(),
            asset_class="crypto",
            regime=MarketRegime.BULL,
            quality_score=ForecastQualityEngine().score(mismatched),
            consensus_result=consensus_result(),
            evidence_records=(evidence(),),
        )


def test_explanation_contains_evidence_factors() -> None:
    result = AdaptiveConfidenceCalibrationEngine().calibrate(
        request(),
        (evidence(),),
    )

    assert len(result.explanation) == 5
    assert "Historical reliability score" in result.explanation[1]
    assert "Evidence support" in result.explanation[2]

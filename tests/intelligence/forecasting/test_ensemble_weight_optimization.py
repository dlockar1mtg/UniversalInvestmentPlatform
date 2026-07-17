"""Tests for Phase 4.2.4 ensemble weight optimization."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.intelligence import (
    CalibrationStrength,
    ConfidenceCalibrationResult,
    EnsembleModelSignal,
    EnsembleWeightOptimizationEngine,
    EnsembleWeightOptimizationService,
    EnsembleWeightProfile,
    ForecastModelEvidence,
    ForecastQualityEngine,
    MarketRegime,
    WeightOptimizationStatus,
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


def signal(
    *,
    name: str,
    version: str = "1.0.0",
    quality: float = 0.80,
    confidence: float = 0.80,
    alignment: float = 0.80,
    reliability: float = 0.80,
    regime_match: float = 1.0,
    eligible: bool = True,
) -> EnsembleModelSignal:
    return EnsembleModelSignal(
        engine_name=name,
        engine_version=version,
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        regime=MarketRegime.BULL,
        model_quality_score=quality,
        calibrated_confidence=confidence,
        consensus_alignment_score=alignment,
        reliability_score=reliability,
        regime_match_score=regime_match,
        eligible=eligible,
    )


def forecast(name: str, value: float) -> UniversalForecast:
    return UniversalForecast(
        asset_id="BTC-USD",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100_000.0,
        point_forecast=value,
        currency="USD",
        provenance=ForecastProvenance(
            model_name=name,
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        confidence_score=0.75,
        expected_return=(value / 100_000.0) - 1.0,
    )


def quality_score(name: str, score: float = 0.80):
    item = ForecastModelEvidence(
        engine_name=name,
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=250,
        accuracy_score=score,
        calibration_score=score,
        directional_accuracy=score,
        stability_score=score,
        coverage_score=score,
    )
    return ForecastQualityEngine().score(item)


def calibration_result(
    confidence: float,
    reliability: float,
) -> ConfidenceCalibrationResult:
    return ConfidenceCalibrationResult(
        raw_confidence=0.70,
        calibrated_confidence=confidence,
        adjustment=confidence - 0.70,
        reliability_score=reliability,
        sample_factor=1.0,
        freshness_factor=1.0,
        regime_match_score=1.0,
        evidence_count=1,
        strength=CalibrationStrength.STRONG,
        selected_evidence=None,
    )


def consensus_result() -> ForecastConsensusResult:
    return ForecastConsensusResult(
        asset_id="BTC-USD",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        model_count=3,
        consensus_value=112_000.0,
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
        EnsembleWeightProfile(quality_weight=0.50)


def test_higher_quality_model_receives_higher_weight() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="strong", quality=0.95),
            signal(name="weak", quality=0.50),
        )
    )

    weights = {
        item.engine_name: item.constrained_weight
        for item in result.weights
    }
    assert weights["strong"] > weights["weak"]
    assert sum(weights.values()) == pytest.approx(1.0)


def test_weights_sum_to_one() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="a", quality=0.90),
            signal(name="b", quality=0.70),
            signal(name="c", quality=0.60),
        )
    )

    assert sum(
        item.constrained_weight for item in result.weights
    ) == pytest.approx(1.0)


def test_maximum_weight_constraint_is_applied() -> None:
    engine = EnsembleWeightOptimizationEngine(
        EnsembleWeightProfile(maximum_model_weight=0.60)
    )
    result = engine.optimize(
        (
            signal(
                name="dominant",
                quality=1.0,
                confidence=1.0,
                alignment=1.0,
                reliability=1.0,
            ),
            signal(
                name="weak-a",
                quality=0.05,
                confidence=0.05,
                alignment=0.05,
                reliability=0.05,
                regime_match=0.05,
            ),
            signal(
                name="weak-b",
                quality=0.05,
                confidence=0.05,
                alignment=0.05,
                reliability=0.05,
                regime_match=0.05,
            ),
        )
    )

    assert max(
        item.constrained_weight for item in result.weights
    ) <= 0.60 + 1e-9


def test_minimum_weight_constraint_is_applied() -> None:
    engine = EnsembleWeightOptimizationEngine(
        EnsembleWeightProfile(
            minimum_model_weight=0.10,
            maximum_model_weight=0.80,
        )
    )
    result = engine.optimize(
        (
            signal(name="a", quality=1.0),
            signal(
                name="b",
                quality=0.01,
                confidence=0.01,
                alignment=0.01,
                reliability=0.01,
                regime_match=0.01,
            ),
        )
    )

    assert min(
        item.constrained_weight for item in result.weights
    ) >= 0.10 - 1e-9


def test_ineligible_model_is_excluded() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="a"),
            signal(name="b"),
            signal(name="excluded", eligible=False),
        )
    )

    assert result.eligible_model_count == 2
    assert result.excluded_model_count == 1
    assert "excluded" not in {
        item.engine_name for item in result.weights
    }


def test_insufficient_eligible_models_returns_status() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="a"),
            signal(name="b", eligible=False),
        )
    )

    assert result.status is WeightOptimizationStatus.INSUFFICIENT
    assert result.weights == ()


def test_duplicate_models_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate model versions"):
        EnsembleWeightOptimizationEngine().optimize(
            (
                signal(name="a"),
                signal(name="a"),
            )
        )


def test_mismatched_regimes_are_rejected() -> None:
    other = EnsembleModelSignal(
        engine_name="b",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        regime=MarketRegime.BEAR,
        model_quality_score=0.8,
        calibrated_confidence=0.8,
        consensus_alignment_score=0.8,
        reliability_score=0.8,
        regime_match_score=1.0,
    )

    with pytest.raises(ValueError, match="same regime"):
        EnsembleWeightOptimizationEngine().optimize(
            (signal(name="a"), other)
        )


def test_equal_zero_scores_use_fallback_weights() -> None:
    zero = dict(
        quality=0.0,
        confidence=0.0,
        alignment=0.0,
        reliability=0.0,
        regime_match=0.0,
    )
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="a", **zero),
            signal(name="b", **zero),
        )
    )

    assert result.status is WeightOptimizationStatus.FALLBACK_EQUAL
    assert all(
        item.constrained_weight == pytest.approx(0.50)
        for item in result.weights
    )


def test_result_is_sorted_by_final_weight() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="weak", quality=0.40),
            signal(name="strong", quality=0.95),
            signal(name="middle", quality=0.70),
        )
    )

    weights = [
        item.constrained_weight for item in result.weights
    ]
    assert weights == sorted(weights, reverse=True)


def test_entry_explanation_identifies_strongest_factor() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(
                name="a",
                quality=0.95,
                confidence=0.70,
                alignment=0.60,
                reliability=0.50,
            ),
            signal(name="b"),
        )
    )

    entry = next(
        item for item in result.weights if item.engine_name == "a"
    )
    assert "Strongest contributing factor" in entry.explanation[1]


def test_service_joins_quality_calibration_and_consensus() -> None:
    result = EnsembleWeightOptimizationService().optimize(
        (
            forecast("model-a", 110_000.0),
            forecast("model-b", 114_000.0),
        ),
        (
            quality_score("model-a", 0.80),
            quality_score("model-b", 0.90),
        ),
        (
            calibration_result(0.78, 0.82),
            calibration_result(0.88, 0.90),
        ),
        consensus_result=consensus_result(),
        asset_class="crypto",
        regime=MarketRegime.BULL,
    )

    assert result.status is WeightOptimizationStatus.OPTIMIZED
    assert len(result.weights) == 2
    assert result.weights[0].engine_name == "model-b"


def test_service_requires_one_calibration_per_forecast() -> None:
    with pytest.raises(ValueError, match="one calibration result"):
        EnsembleWeightOptimizationService().optimize(
            (
                forecast("model-a", 110_000.0),
                forecast("model-b", 114_000.0),
            ),
            (
                quality_score("model-a"),
                quality_score("model-b"),
            ),
            (calibration_result(0.80, 0.80),),
            consensus_result=consensus_result(),
            asset_class="crypto",
            regime=MarketRegime.BULL,
        )


def test_service_rejects_missing_quality_score() -> None:
    with pytest.raises(ValueError, match="Missing quality score"):
        EnsembleWeightOptimizationService().optimize(
            (
                forecast("model-a", 110_000.0),
                forecast("model-b", 114_000.0),
            ),
            (quality_score("model-a"),),
            (
                calibration_result(0.80, 0.80),
                calibration_result(0.80, 0.80),
            ),
            consensus_result=consensus_result(),
            asset_class="crypto",
            regime=MarketRegime.BULL,
        )


def test_result_explanation_identifies_leading_model() -> None:
    result = EnsembleWeightOptimizationEngine().optimize(
        (
            signal(name="a", quality=0.95),
            signal(name="b", quality=0.60),
        )
    )

    assert "Highest weight assigned" in result.explanation[1]

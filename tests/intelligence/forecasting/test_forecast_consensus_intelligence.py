"""Tests for Phase 4.2.2 forecast consensus intelligence."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.intelligence import (
    ForecastModelEvidence,
    ForecastQualityEngine,
)
from foundation.intelligence.forecasting.intelligence.consensus_contracts import (
    ConsensusProfile,
    ConsensusStrength,
    ForecastConsensusInput,
)
from foundation.intelligence.forecasting.intelligence.consensus_engine import (
    ForecastConsensusEngine,
)
from foundation.intelligence.forecasting.intelligence.consensus_service import (
    ForecastConsensusService,
)
from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)


def consensus_input(
    *,
    name: str,
    version: str = "1.0.0",
    value: float,
    direction: ForecastDirection = ForecastDirection.UP,
    quality: float = 0.80,
    asset_id: str = "BTC-USD",
    asset_class: str = "crypto",
    horizon: ForecastHorizon = ForecastHorizon.ONE_YEAR,
    reference_value: float = 100_000.0,
) -> ForecastConsensusInput:
    return ForecastConsensusInput(
        engine_name=name,
        engine_version=version,
        asset_id=asset_id,
        asset_class=asset_class,
        horizon=horizon,
        reference_value=reference_value,
        point_forecast=value,
        direction=direction,
        model_quality=quality,
    )


def universal_forecast(
    *,
    name: str,
    value: float,
    direction: ForecastDirection,
) -> UniversalForecast:
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
        direction=direction,
        expected_return=(value / 100_000.0) - 1.0,
    )


def quality_score(name: str, accuracy: float = 0.80):
    evidence = ForecastModelEvidence(
        engine_name=name,
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=200,
        accuracy_score=accuracy,
        calibration_score=accuracy,
        directional_accuracy=accuracy,
        stability_score=accuracy,
        coverage_score=accuracy,
    )
    return ForecastQualityEngine().score(evidence)


def test_consensus_profile_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        ConsensusProfile(value_agreement_weight=0.70)


def test_input_expected_return_is_calculated() -> None:
    item = consensus_input(name="a", value=110_000.0)

    assert item.expected_return == pytest.approx(0.10)


def test_identical_forecasts_produce_very_strong_consensus() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(name="a", value=110_000.0),
            consensus_input(name="b", value=110_000.0),
            consensus_input(name="c", value=110_000.0),
        )
    )

    assert result.consensus_value == pytest.approx(110_000.0)
    assert result.value_agreement_score == pytest.approx(1.0)
    assert result.direction_agreement_score == pytest.approx(1.0)
    assert result.consensus_score == pytest.approx(1.0)
    assert result.strength is ConsensusStrength.VERY_STRONG
    assert result.confidence_adjustment > 0
    assert result.outliers == ()


def test_quality_weighted_consensus_favors_stronger_model() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(
                name="strong",
                value=120_000.0,
                quality=0.90,
            ),
            consensus_input(
                name="weak",
                value=100_000.0,
                quality=0.10,
            ),
        )
    )

    assert result.consensus_value == pytest.approx(118_000.0)


def test_direction_agreement_uses_majority_vote() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(
                name="a",
                value=110_000.0,
                direction=ForecastDirection.UP,
            ),
            consensus_input(
                name="b",
                value=108_000.0,
                direction=ForecastDirection.UP,
            ),
            consensus_input(
                name="c",
                value=95_000.0,
                direction=ForecastDirection.DOWN,
            ),
        )
    )

    assert result.consensus_direction is ForecastDirection.UP
    assert result.direction_agreement_score == pytest.approx(2 / 3)


def test_widely_dispersed_forecasts_reduce_consensus() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(name="a", value=50_000.0),
            consensus_input(name="b", value=100_000.0),
            consensus_input(name="c", value=150_000.0),
        )
    )

    assert result.dispersion_ratio is not None
    assert result.dispersion_ratio > 0.40
    assert result.consensus_score < 0.90


def test_extreme_forecast_is_detected_as_outlier() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(name="a", value=100_000.0),
            consensus_input(name="b", value=101_000.0),
            consensus_input(name="c", value=99_000.0),
            consensus_input(name="extreme", value=200_000.0),
        )
    )

    assert len(result.outliers) == 1
    assert result.outliers[0].engine_name == "extreme"
    assert "Outlier forecasts detected" in result.explanation[-1]


def test_single_model_returns_insufficient_consensus() -> None:
    result = ForecastConsensusEngine().analyze(
        (consensus_input(name="a", value=110_000.0),)
    )

    assert result.strength is ConsensusStrength.INSUFFICIENT
    assert result.consensus_score == 0.0
    assert result.confidence_adjustment < 0


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="At least one forecast"):
        ForecastConsensusEngine().analyze(())


def test_mismatched_asset_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="same asset_id"):
        ForecastConsensusEngine().analyze(
            (
                consensus_input(name="a", value=100_000.0),
                consensus_input(
                    name="b",
                    value=101_000.0,
                    asset_id="ETH-USD",
                ),
            )
        )


def test_mismatched_horizons_are_rejected() -> None:
    with pytest.raises(ValueError, match="same horizon"):
        ForecastConsensusEngine().analyze(
            (
                consensus_input(name="a", value=100_000.0),
                consensus_input(
                    name="b",
                    value=101_000.0,
                    horizon=ForecastHorizon.FIVE_YEARS,
                ),
            )
        )


def test_duplicate_model_versions_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate model versions"):
        ForecastConsensusEngine().analyze(
            (
                consensus_input(name="a", value=100_000.0),
                consensus_input(name="a", value=101_000.0),
            )
        )


def test_quality_agreement_declines_when_quality_scores_diverge() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(
                name="a",
                value=100_000.0,
                quality=1.0,
            ),
            consensus_input(
                name="b",
                value=100_000.0,
                quality=0.2,
            ),
        )
    )

    assert result.quality_agreement_score == pytest.approx(0.2)


def test_consensus_service_joins_forecasts_to_quality_scores() -> None:
    result = ForecastConsensusService().analyze(
        (
            universal_forecast(
                name="model-a",
                value=110_000.0,
                direction=ForecastDirection.UP,
            ),
            universal_forecast(
                name="model-b",
                value=112_000.0,
                direction=ForecastDirection.UP,
            ),
        ),
        (
            quality_score("model-a", 0.80),
            quality_score("model-b", 0.90),
        ),
        asset_class="crypto",
    )

    assert result.model_count == 2
    assert result.consensus_direction is ForecastDirection.UP
    assert result.consensus_value is not None


def test_consensus_service_rejects_missing_quality_score() -> None:
    with pytest.raises(ValueError, match="Missing quality score"):
        ForecastConsensusService().analyze(
            (
                universal_forecast(
                    name="model-a",
                    value=110_000.0,
                    direction=ForecastDirection.UP,
                ),
                universal_forecast(
                    name="model-b",
                    value=112_000.0,
                    direction=ForecastDirection.UP,
                ),
            ),
            (quality_score("model-a"),),
            asset_class="crypto",
        )


def test_consensus_explanation_contains_core_metrics() -> None:
    result = ForecastConsensusEngine().analyze(
        (
            consensus_input(name="a", value=109_000.0),
            consensus_input(name="b", value=111_000.0),
        )
    )

    assert len(result.explanation) == 4
    assert "Directional agreement" in result.explanation[1]
    assert "dispersion ratio" in result.explanation[2]

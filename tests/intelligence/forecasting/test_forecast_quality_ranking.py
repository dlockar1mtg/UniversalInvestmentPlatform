"""Tests for Phase 4.2.1 forecast quality and ranking foundation."""

from __future__ import annotations

from datetime import date

import pytest

from foundation.intelligence.forecasting.intelligence import (
    ForecastModelEvidence,
    ForecastModelRankingEngine,
    ForecastModelSelectionService,
    ForecastQualityEngine,
    ForecastQualityGrade,
    ForecastQualityProfile,
)
from foundation.intelligence.forecasting.models import ForecastHorizon


def evidence(
    *,
    name: str = "model-a",
    version: str = "1.0.0",
    asset_class: str = "crypto",
    horizon: ForecastHorizon = ForecastHorizon.ONE_YEAR,
    evaluation_date: date = date(2026, 7, 17),
    sample_size: int = 200,
    accuracy: float = 0.80,
    calibration: float = 0.80,
    directional: float = 0.80,
    stability: float = 0.80,
    coverage: float = 0.80,
    bias: float = 0.0,
) -> ForecastModelEvidence:
    return ForecastModelEvidence(
        engine_name=name,
        engine_version=version,
        asset_class=asset_class,
        horizon=horizon,
        evaluation_date=evaluation_date,
        sample_size=sample_size,
        accuracy_score=accuracy,
        calibration_score=calibration,
        directional_accuracy=directional,
        stability_score=stability,
        coverage_score=coverage,
        bias_score=bias,
    )


def test_default_quality_profile_weights_sum_to_one() -> None:
    ForecastQualityProfile()


def test_quality_profile_rejects_invalid_weight_total() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        ForecastQualityProfile(accuracy_weight=0.50)


def test_evidence_freezes_metadata() -> None:
    item = ForecastModelEvidence(
        engine_name="model-a",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=200,
        accuracy_score=0.80,
        calibration_score=0.80,
        directional_accuracy=0.80,
        stability_score=0.80,
        coverage_score=0.80,
        metadata={"source": "backtest"},
    )

    with pytest.raises(TypeError):
        item.metadata["source"] = "changed"


def test_quality_engine_calculates_weighted_raw_score() -> None:
    engine = ForecastQualityEngine()

    score = engine.score(evidence())

    assert score.raw_score == pytest.approx(0.80)
    assert score.adjusted_score == pytest.approx(0.80)
    assert score.eligible is True
    assert score.grade is ForecastQualityGrade.STRONG


def test_small_sample_reduces_score_and_eligibility() -> None:
    engine = ForecastQualityEngine()

    score = engine.score(evidence(sample_size=20))

    assert score.sample_factor == pytest.approx(0.10)
    assert score.eligible is False
    assert score.grade is ForecastQualityGrade.INSUFFICIENT
    assert "Insufficient historical sample size." in score.reasons


def test_stale_evidence_becomes_ineligible() -> None:
    engine = ForecastQualityEngine()

    score = engine.score(
        evidence(evaluation_date=date(2025, 1, 1)),
        as_of_date=date(2026, 7, 17),
    )

    assert score.freshness_factor == 0.0
    assert score.eligible is False
    assert "Historical evidence is stale." in score.reasons


def test_bias_applies_penalty() -> None:
    engine = ForecastQualityEngine()

    score = engine.score(evidence(bias=0.25))

    assert score.bias_penalty == pytest.approx(0.25)
    assert score.adjusted_score == pytest.approx(0.60)
    assert "Material forecast bias detected." in score.reasons


def test_future_evaluation_date_is_rejected() -> None:
    engine = ForecastQualityEngine()

    with pytest.raises(ValueError, match="cannot be after"):
        engine.score(
            evidence(evaluation_date=date(2026, 7, 18)),
            as_of_date=date(2026, 7, 17),
        )


def test_ranking_places_highest_quality_first() -> None:
    ranking = ForecastModelRankingEngine().rank(
        (
            evidence(name="weaker", accuracy=0.60, calibration=0.60),
            evidence(name="stronger", accuracy=0.90, calibration=0.90),
        )
    )

    assert ranking[0].rank == 1
    assert ranking[0].engine_name == "stronger"
    assert ranking[1].engine_name == "weaker"


def test_ranking_places_eligible_models_before_ineligible_models() -> None:
    ranking = ForecastModelRankingEngine().rank(
        (
            evidence(name="ineligible", sample_size=5, accuracy=1.0),
            evidence(name="eligible", accuracy=0.70),
        )
    )

    assert ranking[0].engine_name == "eligible"
    assert ranking[0].quality.eligible is True
    assert ranking[1].quality.eligible is False


def test_ranking_eligible_only_filters_failed_models() -> None:
    ranking = ForecastModelRankingEngine().rank(
        (
            evidence(name="eligible"),
            evidence(name="small", sample_size=1),
        ),
        eligible_only=True,
    )

    assert len(ranking) == 1
    assert ranking[0].engine_name == "eligible"


def test_ranking_tie_breaker_is_deterministic() -> None:
    ranking = ForecastModelRankingEngine().rank(
        (
            evidence(name="z-model"),
            evidence(name="a-model"),
        )
    )

    assert [entry.engine_name for entry in ranking] == [
        "a-model",
        "z-model",
    ]


def test_selection_filters_asset_class_and_horizon() -> None:
    service = ForecastModelSelectionService()

    result = service.select(
        (
            evidence(name="crypto-1y"),
            evidence(
                name="metals-1y",
                asset_class="metals",
            ),
            evidence(
                name="crypto-5y",
                horizon=ForecastHorizon.FIVE_YEARS,
            ),
        ),
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
    )

    assert result.selected is not None
    assert result.selected.engine_name == "crypto-1y"
    assert len(result.rankings) == 1


def test_selection_returns_none_when_no_evidence_matches() -> None:
    result = ForecastModelSelectionService().select(
        (evidence(asset_class="metals"),),
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
    )

    assert result.selected is None
    assert result.rankings == ()
    assert "No historical model evidence matched" in result.selection_reason


def test_selection_returns_none_when_all_models_are_ineligible() -> None:
    result = ForecastModelSelectionService().select(
        (evidence(sample_size=2),),
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
    )

    assert result.selected is None
    assert len(result.rankings) == 1
    assert "no model met" in result.selection_reason


def test_selection_reason_identifies_selected_model() -> None:
    result = ForecastModelSelectionService().select(
        (evidence(name="winner", version="2.1.0"),),
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
    )

    assert result.selected is not None
    assert "winner 2.1.0" in result.selection_reason

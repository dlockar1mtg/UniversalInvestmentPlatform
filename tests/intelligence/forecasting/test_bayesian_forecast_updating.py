"""Tests for Phase 4.3.3 Bayesian forecast updating."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)
from foundation.intelligence.forecasting.probability import (
    BayesianForecastUpdateEngine,
    BayesianForecastUpdateService,
    BayesianUpdateFamily,
    BayesianUpdateRequest,
    BayesianUpdateStatus,
    BetaPrior,
    BinomialEvidence,
    DistributionFamily,
    NormalEvidence,
    NormalPrior,
)


def forecast() -> UniversalForecast:
    return UniversalForecast(
        forecast_id="forecast-001",
        asset_id="TEST",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        point_forecast=110.0,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="bayes-model",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        confidence_score=0.80,
        expected_return=0.10,
    )


def normal_request(
    evidence: tuple[NormalEvidence, ...] = (),
) -> BayesianUpdateRequest:
    return BayesianUpdateRequest(
        asset_id="TEST",
        asset_class="equity",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        currency="USD",
        model_name="bayes-model",
        model_version="1.0.0",
        family=BayesianUpdateFamily.NORMAL_NORMAL,
        normal_prior=NormalPrior(mean=110.0, variance=100.0),
        normal_evidence=evidence,
        target_value=120.0,
    )


def beta_request(
    evidence: tuple[BinomialEvidence, ...] = (),
) -> BayesianUpdateRequest:
    return BayesianUpdateRequest(
        asset_id="TEST-EVENT",
        asset_class="macro",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=0.50,
        currency="PROBABILITY",
        model_name="bayes-event-model",
        model_version="1.0.0",
        family=BayesianUpdateFamily.BETA_BINOMIAL,
        beta_prior=BetaPrior(alpha=2.0, beta=2.0),
        binomial_evidence=evidence,
        target_value=0.70,
    )


def test_normal_prior_requires_positive_variance() -> None:
    with pytest.raises(ValueError, match="variance must be positive"):
        NormalPrior(mean=0.0, variance=0.0)


def test_normal_evidence_requires_positive_sample_size() -> None:
    with pytest.raises(ValueError, match="sample_size"):
        NormalEvidence(
            sample_mean=100.0,
            observation_variance=25.0,
            sample_size=0,
            evidence_date=date(2026, 7, 17),
            source="test",
        )


def test_beta_prior_mean() -> None:
    prior = BetaPrior(alpha=3.0, beta=1.0)

    assert prior.mean == pytest.approx(0.75)


def test_binomial_evidence_validates_successes() -> None:
    with pytest.raises(ValueError, match="between zero and trials"):
        BinomialEvidence(
            successes=11,
            trials=10,
            evidence_date=date(2026, 7, 17),
            source="test",
        )


def test_request_requires_matching_family_inputs() -> None:
    with pytest.raises(ValueError, match="normal_prior is required"):
        BayesianUpdateRequest(
            asset_id="TEST",
            asset_class="equity",
            as_of_date=date(2026, 7, 17),
            target_date=date(2027, 7, 17),
            horizon=ForecastHorizon.ONE_YEAR,
            reference_value=100.0,
            currency="USD",
            model_name="model",
            model_version="1.0.0",
            family=BayesianUpdateFamily.NORMAL_NORMAL,
        )


def test_normal_update_moves_toward_evidence() -> None:
    evidence = (
        NormalEvidence(
            sample_mean=120.0,
            observation_variance=25.0,
            sample_size=10,
            evidence_date=date(2026, 7, 17),
            source="market",
        ),
    )
    result = BayesianForecastUpdateEngine().update(
        normal_request(evidence)
    )

    posterior_mean = result.posterior_parameters["mean"]
    assert 110.0 < posterior_mean < 120.0
    assert result.diagnostics.status is BayesianUpdateStatus.UPDATED


def test_normal_update_reduces_variance() -> None:
    evidence = (
        NormalEvidence(
            sample_mean=112.0,
            observation_variance=16.0,
            sample_size=20,
            evidence_date=date(2026, 7, 17),
            source="market",
        ),
    )
    result = BayesianForecastUpdateEngine().update(
        normal_request(evidence)
    )

    assert result.posterior_parameters["variance"] < 100.0


def test_normal_no_evidence_preserves_prior() -> None:
    result = BayesianForecastUpdateEngine().update(
        normal_request()
    )

    assert result.posterior_parameters["mean"] == pytest.approx(110.0)
    assert result.posterior_parameters["variance"] == pytest.approx(100.0)
    assert result.diagnostics.status is BayesianUpdateStatus.NO_EVIDENCE


def test_normal_distribution_contains_credible_intervals() -> None:
    result = BayesianForecastUpdateEngine().update(
        normal_request()
    )

    assert result.distribution.central_interval(0.90).coverage == 0.90
    assert result.distribution.percentile(0.50).value == pytest.approx(
        result.distribution.statistics.median
    )


def test_normal_distribution_contains_probabilities() -> None:
    result = BayesianForecastUpdateEngine().update(
        normal_request()
    )
    distribution = result.distribution

    assert 0.0 <= distribution.probability_above_reference <= 1.0
    assert 0.0 <= distribution.probability_below_reference <= 1.0
    assert 0.0 <= distribution.probability_above_target <= 1.0


def test_beta_update_matches_closed_form() -> None:
    evidence = (
        BinomialEvidence(
            successes=8,
            trials=10,
            evidence_date=date(2026, 7, 17),
            source="validation",
        ),
    )
    result = BayesianForecastUpdateEngine().update(
        beta_request(evidence)
    )

    assert result.posterior_parameters["alpha"] == pytest.approx(10.0)
    assert result.posterior_parameters["beta"] == pytest.approx(4.0)
    assert result.posterior_parameters["mean"] == pytest.approx(10 / 14)


def test_beta_weighted_evidence_is_supported() -> None:
    evidence = (
        BinomialEvidence(
            successes=8,
            trials=10,
            evidence_date=date(2026, 7, 17),
            source="validation",
            weight=0.5,
        ),
    )
    result = BayesianForecastUpdateEngine().update(
        beta_request(evidence)
    )

    assert result.posterior_parameters["alpha"] == pytest.approx(6.0)
    assert result.posterior_parameters["beta"] == pytest.approx(3.0)


def test_beta_no_evidence_preserves_prior() -> None:
    result = BayesianForecastUpdateEngine().update(
        beta_request()
    )

    assert result.posterior_parameters["alpha"] == pytest.approx(2.0)
    assert result.posterior_parameters["beta"] == pytest.approx(2.0)
    assert result.diagnostics.status is BayesianUpdateStatus.NO_EVIDENCE


def test_beta_distribution_is_bounded() -> None:
    result = BayesianForecastUpdateEngine().update(
        beta_request()
    )
    stats = result.distribution.statistics

    assert stats.minimum == 0.0
    assert stats.maximum == 1.0
    assert 0.0 <= stats.mean <= 1.0
    assert 0.0 <= stats.median <= 1.0


def test_beta_percentiles_are_ordered() -> None:
    result = BayesianForecastUpdateEngine().update(
        beta_request()
    )

    values = [
        item.value for item in result.distribution.percentiles
    ]
    assert values == sorted(values)


def test_beta_probability_metrics_are_bounded() -> None:
    result = BayesianForecastUpdateEngine().update(
        beta_request()
    )
    distribution = result.distribution

    assert 0.0 <= distribution.probability_above_reference <= 1.0
    assert 0.0 <= distribution.probability_below_reference <= 1.0
    assert 0.0 <= distribution.probability_above_target <= 1.0


def test_distribution_family_is_bayesian_posterior() -> None:
    normal_result = BayesianForecastUpdateEngine().update(
        normal_request()
    )
    beta_result = BayesianForecastUpdateEngine().update(
        beta_request()
    )

    assert normal_result.distribution.family is (
        DistributionFamily.BAYESIAN_POSTERIOR
    )
    assert beta_result.distribution.family is (
        DistributionFamily.BAYESIAN_POSTERIOR
    )


def test_continuous_service_builds_update_from_forecast() -> None:
    result = BayesianForecastUpdateService().update_continuous_forecast(
        forecast(),
        asset_class="equity",
        prior_variance=100.0,
        evidence=(
            NormalEvidence(
                sample_mean=115.0,
                observation_variance=25.0,
                sample_size=10,
                evidence_date=date(2026, 7, 17),
                source="market",
            ),
        ),
        target_value=120.0,
    )

    assert result.distribution.asset_id == "TEST"
    assert result.distribution.metadata["source_forecast_id"] == (
        "forecast-001"
    )


def test_binary_service_builds_probability_update() -> None:
    result = BayesianForecastUpdateService().update_binary_probability(
        forecast(),
        asset_class="equity",
        prior=BetaPrior(alpha=3.0, beta=2.0),
        evidence=(
            BinomialEvidence(
                successes=7,
                trials=10,
                evidence_date=date(2026, 7, 17),
                source="validation",
            ),
        ),
        target_probability=0.70,
    )

    assert result.distribution.currency == "PROBABILITY"
    assert result.posterior_parameters["mean"] > 0.50

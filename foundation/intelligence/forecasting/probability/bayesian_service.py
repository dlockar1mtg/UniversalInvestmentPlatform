"""Service integration for Bayesian forecast updating."""

from __future__ import annotations

from ..models import UniversalForecast
from .bayesian_contracts import (
    BayesianUpdateFamily,
    BayesianUpdateRequest,
    BayesianUpdateResult,
    BetaPrior,
    BinomialEvidence,
    NormalEvidence,
    NormalPrior,
)
from .bayesian_engine import BayesianForecastUpdateEngine


class BayesianForecastUpdateService:
    """Construct Bayesian update requests from universal forecasts."""

    def __init__(
        self,
        engine: BayesianForecastUpdateEngine | None = None,
    ) -> None:
        self.engine = engine or BayesianForecastUpdateEngine()

    def update_continuous_forecast(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        prior_variance: float,
        evidence: tuple[NormalEvidence, ...],
        target_value: float | None = None,
    ) -> BayesianUpdateResult:
        request = BayesianUpdateRequest(
            asset_id=forecast.asset_id,
            asset_class=asset_class,
            as_of_date=forecast.as_of_date,
            target_date=forecast.target_date,
            horizon=forecast.horizon,
            reference_value=forecast.reference_value,
            currency=forecast.currency,
            model_name=forecast.provenance.model_name,
            model_version=forecast.provenance.model_version,
            family=BayesianUpdateFamily.NORMAL_NORMAL,
            normal_prior=NormalPrior(
                mean=forecast.point_forecast,
                variance=prior_variance,
            ),
            normal_evidence=evidence,
            target_value=target_value,
            metadata={
                "source_forecast_id": forecast.forecast_id,
                "source_confidence": forecast.confidence_score,
            },
        )
        return self.engine.update(request)

    def update_binary_probability(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        prior: BetaPrior,
        evidence: tuple[BinomialEvidence, ...],
        target_probability: float | None = None,
    ) -> BayesianUpdateResult:
        request = BayesianUpdateRequest(
            asset_id=forecast.asset_id,
            asset_class=asset_class,
            as_of_date=forecast.as_of_date,
            target_date=forecast.target_date,
            horizon=forecast.horizon,
            reference_value=prior.mean,
            currency="PROBABILITY",
            model_name=forecast.provenance.model_name,
            model_version=forecast.provenance.model_version,
            family=BayesianUpdateFamily.BETA_BINOMIAL,
            beta_prior=prior,
            binomial_evidence=evidence,
            target_value=target_probability,
            metadata={
                "source_forecast_id": forecast.forecast_id,
                "source_confidence": forecast.confidence_score,
            },
        )
        return self.engine.update(request)

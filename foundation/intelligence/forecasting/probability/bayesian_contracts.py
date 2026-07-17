"""Contracts for Bayesian forecast updating."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastHorizon


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


class BayesianUpdateFamily(str, Enum):
    """Supported conjugate Bayesian update families."""

    NORMAL_NORMAL = "normal_normal"
    BETA_BINOMIAL = "beta_binomial"


class BayesianUpdateStatus(str, Enum):
    """Outcome of a Bayesian update request."""

    UPDATED = "updated"
    NO_EVIDENCE = "no_evidence"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class NormalPrior:
    """Normal prior for a continuous latent quantity."""

    mean: float
    variance: float

    def __post_init__(self) -> None:
        _require_finite("mean", self.mean)
        _require_finite("variance", self.variance)
        if self.variance <= 0:
            raise ValueError("variance must be positive.")


@dataclass(frozen=True, slots=True)
class NormalEvidence:
    """Continuous evidence summarized by a mean, variance, and sample size."""

    sample_mean: float
    observation_variance: float
    sample_size: int
    evidence_date: date
    source: str
    weight: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_finite("sample_mean", self.sample_mean)
        _require_finite(
            "observation_variance",
            self.observation_variance,
        )
        if self.observation_variance <= 0:
            raise ValueError(
                "observation_variance must be positive."
            )
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        if not self.source.strip():
            raise ValueError("source is required.")
        _require_probability("weight", self.weight)
        if self.weight == 0:
            raise ValueError("weight must be greater than zero.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class BetaPrior:
    """Beta prior for a binary-event probability."""

    alpha: float
    beta: float

    def __post_init__(self) -> None:
        _require_finite("alpha", self.alpha)
        _require_finite("beta", self.beta)
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError("alpha and beta must be positive.")

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


@dataclass(frozen=True, slots=True)
class BinomialEvidence:
    """Binary-event evidence summarized by successes and trials."""

    successes: int
    trials: int
    evidence_date: date
    source: str
    weight: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trials <= 0:
            raise ValueError("trials must be positive.")
        if self.successes < 0 or self.successes > self.trials:
            raise ValueError(
                "successes must be between zero and trials."
            )
        if not self.source.strip():
            raise ValueError("source is required.")
        _require_probability("weight", self.weight)
        if self.weight == 0:
            raise ValueError("weight must be greater than zero.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class BayesianUpdateRequest:
    """Canonical Bayesian update request."""

    asset_id: str
    asset_class: str
    as_of_date: date
    target_date: date
    horizon: ForecastHorizon
    reference_value: float
    currency: str
    model_name: str
    model_version: str
    family: BayesianUpdateFamily
    normal_prior: NormalPrior | None = None
    beta_prior: BetaPrior | None = None
    normal_evidence: tuple[NormalEvidence, ...] = ()
    binomial_evidence: tuple[BinomialEvidence, ...] = ()
    target_value: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "asset_id",
            "asset_class",
            "currency",
            "model_name",
            "model_version",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required.")
        if self.target_date <= self.as_of_date:
            raise ValueError("target_date must be after as_of_date.")
        _require_finite("reference_value", self.reference_value)
        if self.reference_value <= 0:
            raise ValueError("reference_value must be positive.")
        _require_finite("target_value", self.target_value)

        if self.family is BayesianUpdateFamily.NORMAL_NORMAL:
            if self.normal_prior is None:
                raise ValueError(
                    "normal_prior is required for normal-normal updating."
                )
            if self.beta_prior is not None or self.binomial_evidence:
                raise ValueError(
                    "Beta-binomial inputs are not valid for "
                    "normal-normal updating."
                )
        elif self.family is BayesianUpdateFamily.BETA_BINOMIAL:
            if self.beta_prior is None:
                raise ValueError(
                    "beta_prior is required for beta-binomial updating."
                )
            if self.normal_prior is not None or self.normal_evidence:
                raise ValueError(
                    "Normal-normal inputs are not valid for "
                    "beta-binomial updating."
                )

        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class BayesianUpdateDiagnostics:
    """Diagnostics describing posterior formation."""

    family: BayesianUpdateFamily
    status: BayesianUpdateStatus
    evidence_count: int
    effective_sample_size: float
    prior_weight: float
    evidence_weight: float
    posterior_shift: float
    explanation: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.evidence_count < 0:
            raise ValueError("evidence_count cannot be negative.")
        for name in (
            "effective_sample_size",
            "prior_weight",
            "evidence_weight",
            "posterior_shift",
        ):
            _require_finite(name, getattr(self, name))
        if self.effective_sample_size < 0:
            raise ValueError(
                "effective_sample_size cannot be negative."
            )
        if self.prior_weight < 0 or self.evidence_weight < 0:
            raise ValueError("Weights cannot be negative.")
        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))


@dataclass(frozen=True, slots=True)
class BayesianUpdateResult:
    """Posterior distribution and update diagnostics."""

    distribution: Any
    diagnostics: BayesianUpdateDiagnostics
    posterior_parameters: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "posterior_parameters",
            _freeze_mapping(self.posterior_parameters),
        )

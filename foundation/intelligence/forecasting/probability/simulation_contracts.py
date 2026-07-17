"""Contracts for deterministic Monte Carlo forecast simulation."""

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


def _require_finite(name: str, value: float) -> None:
    if not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


class SimulationProcess(str, Enum):
    """Supported stochastic return processes."""

    GEOMETRIC_BROWNIAN_MOTION = "geometric_brownian_motion"
    ARITHMETIC_BROWNIAN_MOTION = "arithmetic_brownian_motion"


@dataclass(frozen=True, slots=True)
class MonteCarloSimulationProfile:
    """Configuration for Monte Carlo path generation."""

    simulation_count: int = 10_000
    steps: int = 252
    annual_drift: float = 0.08
    annual_volatility: float = 0.25
    process: SimulationProcess = SimulationProcess.GEOMETRIC_BROWNIAN_MOTION
    random_seed: int = 42
    percentile_levels: tuple[float, ...] = (
        0.05,
        0.25,
        0.50,
        0.75,
        0.95,
    )
    interval_coverages: tuple[float, ...] = (0.50, 0.90)
    var_confidence_levels: tuple[float, ...] = (0.95,)
    floor_value: float | None = 0.0
    store_paths: bool = False
    maximum_stored_paths: int = 100
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.simulation_count <= 0:
            raise ValueError("simulation_count must be positive.")
        if self.steps <= 0:
            raise ValueError("steps must be positive.")
        _require_finite("annual_drift", self.annual_drift)
        if self.annual_volatility < 0:
            raise ValueError("annual_volatility cannot be negative.")
        _require_finite("annual_volatility", self.annual_volatility)

        for name, values in (
            ("percentile_levels", self.percentile_levels),
            ("interval_coverages", self.interval_coverages),
            ("var_confidence_levels", self.var_confidence_levels),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{name} values must be unique.")
            for value in values:
                _require_probability(f"{name}[]", value)

        if 0.50 not in self.percentile_levels:
            raise ValueError("percentile_levels must include 0.50.")
        if any(
            coverage <= 0.0 or coverage >= 1.0
            for coverage in self.interval_coverages
        ):
            raise ValueError(
                "interval coverages must be strictly between 0 and 1."
            )
        if any(
            confidence <= 0.50
            for confidence in self.var_confidence_levels
        ):
            raise ValueError(
                "VaR confidence levels must be greater than 0.50."
            )
        if self.floor_value is not None:
            _require_finite("floor_value", self.floor_value)
        if self.maximum_stored_paths <= 0:
            raise ValueError("maximum_stored_paths must be positive.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class MonteCarloSimulationRequest:
    """One probabilistic forecast simulation request."""

    asset_id: str
    asset_class: str
    as_of_date: date
    target_date: date
    horizon: ForecastHorizon
    reference_value: float
    currency: str
    model_name: str
    model_version: str
    source_forecast_ids: tuple[str, ...] = ()
    source_run_id: str | None = None
    target_value: float | None = None
    profile: MonteCarloSimulationProfile = field(
        default_factory=MonteCarloSimulationProfile
    )
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
        if self.target_value is not None:
            _require_finite("target_value", self.target_value)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class MonteCarloDiagnostics:
    """Simulation execution and numerical diagnostics."""

    simulation_count: int
    steps: int
    random_seed: int
    clipped_value_count: int
    invalid_value_count: int
    terminal_minimum: float
    terminal_maximum: float
    runtime_seconds: float
    stored_path_count: int = 0

    def __post_init__(self) -> None:
        if self.simulation_count <= 0 or self.steps <= 0:
            raise ValueError("simulation_count and steps must be positive.")
        if self.clipped_value_count < 0 or self.invalid_value_count < 0:
            raise ValueError("Diagnostic counts cannot be negative.")
        for name in (
            "terminal_minimum",
            "terminal_maximum",
            "runtime_seconds",
        ):
            _require_finite(name, getattr(self, name))
        if self.terminal_minimum > self.terminal_maximum:
            raise ValueError(
                "terminal_minimum cannot exceed terminal_maximum."
            )
        if self.runtime_seconds < 0:
            raise ValueError("runtime_seconds cannot be negative.")
        if self.stored_path_count < 0:
            raise ValueError("stored_path_count cannot be negative.")


@dataclass(frozen=True, slots=True)
class MonteCarloSimulationResult:
    """Distribution plus optional paths and diagnostics."""

    distribution: Any
    diagnostics: MonteCarloDiagnostics
    terminal_values: tuple[float, ...]
    stored_paths: tuple[tuple[float, ...], ...] = ()

    def __post_init__(self) -> None:
        if len(self.terminal_values) != self.diagnostics.simulation_count:
            raise ValueError(
                "terminal_values count must match simulation_count."
            )
        if len(self.stored_paths) != self.diagnostics.stored_path_count:
            raise ValueError(
                "stored_paths count must match stored_path_count."
            )

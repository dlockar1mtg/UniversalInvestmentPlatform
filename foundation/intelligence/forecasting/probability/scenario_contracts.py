"""Contracts for probabilistic scenario-tree generation."""

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


class ScenarioDirection(str, Enum):
    """Direction of movement represented by a scenario branch."""

    DOWNSIDE = "downside"
    NEUTRAL = "neutral"
    UPSIDE = "upside"


class ScenarioTreeStatus(str, Enum):
    """Lifecycle state of a scenario tree."""

    GENERATED = "generated"
    PRUNED = "pruned"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ScenarioBranchTemplate:
    """Reusable branch definition for one scenario stage."""

    name: str
    probability: float
    return_multiplier: float
    direction: ScenarioDirection
    description: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Branch name is required.")
        _require_probability("probability", self.probability)
        if self.probability <= 0:
            raise ValueError("Branch probability must be greater than zero.")
        _require_finite("return_multiplier", self.return_multiplier)
        if self.return_multiplier < 0:
            raise ValueError("return_multiplier cannot be negative.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ScenarioStageDefinition:
    """One stage of a multi-stage scenario tree."""

    stage_number: int
    label: str
    branches: tuple[ScenarioBranchTemplate, ...]
    stage_date: date | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stage_number <= 0:
            raise ValueError("stage_number must be positive.")
        if not self.label.strip():
            raise ValueError("Stage label is required.")
        if not self.branches:
            raise ValueError("Each stage requires at least one branch.")
        branch_names = [item.name for item in self.branches]
        if len(branch_names) != len(set(branch_names)):
            raise ValueError("Branch names must be unique within a stage.")
        total = sum(item.probability for item in self.branches)
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Stage branch probabilities must sum to 1.0.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ScenarioTreeProfile:
    """Configuration controlling tree generation and pruning."""

    minimum_path_probability: float = 0.0
    maximum_terminal_paths: int | None = None
    renormalize_after_pruning: bool = True
    include_internal_nodes: bool = True
    target_value: float | None = None
    var_confidence_level: float = 0.95
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_probability(
            "minimum_path_probability",
            self.minimum_path_probability,
        )
        if self.maximum_terminal_paths is not None:
            if self.maximum_terminal_paths <= 0:
                raise ValueError(
                    "maximum_terminal_paths must be positive."
                )
        _require_probability(
            "var_confidence_level",
            self.var_confidence_level,
        )
        if self.var_confidence_level <= 0.5:
            raise ValueError(
                "var_confidence_level must be greater than 0.5."
            )
        if self.target_value is not None:
            _require_finite("target_value", self.target_value)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ScenarioTreeRequest:
    """Canonical request for multi-stage scenario-tree generation."""

    asset_id: str
    asset_class: str
    as_of_date: date
    target_date: date
    horizon: ForecastHorizon
    reference_value: float
    currency: str
    model_name: str
    model_version: str
    stages: tuple[ScenarioStageDefinition, ...]
    profile: ScenarioTreeProfile = field(default_factory=ScenarioTreeProfile)
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
        if not self.stages:
            raise ValueError("At least one scenario stage is required.")
        stage_numbers = [item.stage_number for item in self.stages]
        if stage_numbers != sorted(stage_numbers):
            raise ValueError("Scenario stages must be ordered.")
        if len(stage_numbers) != len(set(stage_numbers)):
            raise ValueError("Scenario stage numbers must be unique.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ScenarioTreeNode:
    """One node in the generated scenario tree."""

    node_id: str
    parent_id: str | None
    stage_number: int
    branch_name: str
    direction: ScenarioDirection
    conditional_probability: float
    path_probability: float
    value: float
    cumulative_return: float
    terminal: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required.")
        if self.stage_number < 0:
            raise ValueError("stage_number cannot be negative.")
        if not self.branch_name.strip():
            raise ValueError("branch_name is required.")
        _require_probability(
            "conditional_probability",
            self.conditional_probability,
        )
        _require_probability("path_probability", self.path_probability)
        _require_finite("value", self.value)
        _require_finite("cumulative_return", self.cumulative_return)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ScenarioTerminalOutcome:
    """One terminal path and its probability-weighted outcome."""

    node_id: str
    path: tuple[str, ...]
    probability: float
    terminal_value: float
    total_return: float
    direction: ScenarioDirection

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required.")
        if not self.path:
            raise ValueError("Terminal path cannot be empty.")
        _require_probability("probability", self.probability)
        _require_finite("terminal_value", self.terminal_value)
        _require_finite("total_return", self.total_return)


@dataclass(frozen=True, slots=True)
class ScenarioTreeDiagnostics:
    """Generation, pruning, and probability diagnostics."""

    status: ScenarioTreeStatus
    stage_count: int
    node_count: int
    terminal_path_count: int
    pruned_path_count: int
    original_probability_mass: float
    retained_probability_mass: float
    renormalization_factor: float
    explanation: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "stage_count",
            "node_count",
            "terminal_path_count",
            "pruned_path_count",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative.")
        for name in (
            "original_probability_mass",
            "retained_probability_mass",
            "renormalization_factor",
        ):
            _require_finite(name, getattr(self, name))
        if self.original_probability_mass < 0:
            raise ValueError(
                "original_probability_mass cannot be negative."
            )
        if self.retained_probability_mass < 0:
            raise ValueError(
                "retained_probability_mass cannot be negative."
            )
        if self.renormalization_factor <= 0:
            raise ValueError(
                "renormalization_factor must be positive."
            )
        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))


@dataclass(frozen=True, slots=True)
class ScenarioTreeResult:
    """Generated scenario tree and canonical forecast distribution."""

    distribution: Any
    nodes: tuple[ScenarioTreeNode, ...]
    terminal_outcomes: tuple[ScenarioTerminalOutcome, ...]
    diagnostics: ScenarioTreeDiagnostics

    def __post_init__(self) -> None:
        node_ids = [item.node_id for item in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Scenario tree node ids must be unique.")
        known = set(node_ids)
        for item in self.nodes:
            if item.parent_id is not None and item.parent_id not in known:
                raise ValueError(
                    "Scenario node parent_id must reference a known node."
                )
        if len(self.terminal_outcomes) != (
            self.diagnostics.terminal_path_count
        ):
            raise ValueError(
                "Terminal outcome count must match diagnostics."
            )

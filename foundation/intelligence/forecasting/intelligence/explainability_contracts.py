"""Contracts for explainable forecast intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastDirection, ForecastHorizon
from .calibration_contracts import MarketRegime


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _validate_probability(name: str, value: float) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


class DriverPolarity(str, Enum):
    """Direction of a forecast driver's influence."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EvidenceNodeType(str, Enum):
    """Supported node types in the forecast evidence graph."""

    FORECAST = "forecast"
    QUALITY = "quality"
    CONSENSUS = "consensus"
    CALIBRATION = "calibration"
    ENSEMBLE_WEIGHT = "ensemble_weight"
    DRIVER = "driver"
    RISK = "risk"
    HISTORICAL_ANALOG = "historical_analog"


@dataclass(frozen=True, slots=True)
class ForecastDriver:
    """One attributable driver of the forecast conclusion."""

    name: str
    contribution: float
    importance: float
    polarity: DriverPolarity
    category: str = "general"
    evidence: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Driver name is required.")
        if not self.category.strip():
            raise ValueError("Driver category is required.")
        if not isfinite(float(self.contribution)):
            raise ValueError("Driver contribution must be finite.")
        _validate_probability("importance", self.importance)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ForecastRiskFactor:
    """One risk factor that may weaken forecast reliability."""

    name: str
    severity: float
    description: str
    mitigated: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Risk name is required.")
        if not self.description.strip():
            raise ValueError("Risk description is required.")
        _validate_probability("severity", self.severity)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class HistoricalAnalog:
    """Historical period comparable to the current forecast context."""

    analog_id: str
    label: str
    similarity_score: float
    regime: MarketRegime
    outcome_summary: str
    feature_similarity: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.analog_id.strip() or not self.label.strip():
            raise ValueError("Historical analog id and label are required.")
        if not self.outcome_summary.strip():
            raise ValueError("Historical analog outcome_summary is required.")
        _validate_probability("similarity_score", self.similarity_score)
        for name, value in self.feature_similarity.items():
            _validate_probability(f"feature_similarity[{name}]", value)
        object.__setattr__(
            self,
            "feature_similarity",
            MappingProxyType(dict(self.feature_similarity)),
        )


@dataclass(frozen=True, slots=True)
class EvidenceNode:
    """Node in the auditable forecast evidence graph."""

    node_id: str
    node_type: EvidenceNodeType
    label: str
    score: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.label.strip():
            raise ValueError("Evidence node id and label are required.")
        if self.score is not None:
            _validate_probability("score", self.score)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class EvidenceEdge:
    """Directed relationship between two evidence nodes."""

    source_id: str
    target_id: str
    relationship: str
    strength: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ValueError("Evidence edge endpoints are required.")
        if not self.relationship.strip():
            raise ValueError("Evidence edge relationship is required.")
        _validate_probability("strength", self.strength)


@dataclass(frozen=True, slots=True)
class ForecastEvidenceGraph:
    """Auditable graph of evidence supporting a forecast explanation."""

    nodes: tuple[EvidenceNode, ...]
    edges: tuple[EvidenceEdge, ...]

    def __post_init__(self) -> None:
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Evidence graph node ids must be unique.")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source_id not in known or edge.target_id not in known:
                raise ValueError(
                    "Evidence graph edges must reference known node ids."
                )


@dataclass(frozen=True, slots=True)
class ForecastExplanation:
    """Complete deterministic explanation for one forecast."""

    forecast_id: str
    asset_id: str
    asset_class: str
    horizon: ForecastHorizon
    direction: ForecastDirection
    point_forecast: float
    confidence: float | None
    quality_score: float
    consensus_score: float
    calibrated_confidence: float
    ensemble_weights: Mapping[str, float]
    drivers: tuple[ForecastDriver, ...]
    risks: tuple[ForecastRiskFactor, ...]
    historical_analogs: tuple[HistoricalAnalog, ...]
    evidence_graph: ForecastEvidenceGraph
    narrative: str
    audit_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("forecast_id", "asset_id", "asset_class"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        if not isfinite(float(self.point_forecast)):
            raise ValueError("point_forecast must be finite.")
        if self.confidence is not None:
            _validate_probability("confidence", self.confidence)
        for field_name in (
            "quality_score",
            "consensus_score",
            "calibrated_confidence",
        ):
            _validate_probability(field_name, getattr(self, field_name))
        if not self.narrative.strip():
            raise ValueError("narrative is required.")
        if self.ensemble_weights:
            total = sum(self.ensemble_weights.values())
            if abs(total - 1.0) > 1e-9:
                raise ValueError("ensemble_weights must sum to 1.0.")
            for name, value in self.ensemble_weights.items():
                _validate_probability(f"ensemble_weights[{name}]", value)
        object.__setattr__(
            self,
            "ensemble_weights",
            MappingProxyType(dict(self.ensemble_weights)),
        )
        object.__setattr__(
            self,
            "audit_metadata",
            _freeze_mapping(self.audit_metadata),
        )

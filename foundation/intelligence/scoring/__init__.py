"""Universal scoring contracts and validation utilities."""

from .composite_engine import (
    CompositeDiagnostics,
    CompositeScore,
    CompositeScoringEngine,
)
from .confidence_adjustment import ConfidenceAdjustment, apply_confidence_adjustment
from .dimension_aggregation import (
    DimensionAggregation,
    aggregate_dimension,
    aggregate_dimensions,
)
from .normalization import NormalizationResult
from .normalization_engine import NormalizationEngine
from .normalization_registry import (
    DEFAULT_NORMALIZATION_REGISTRY,
    NormalizationRegistry,
)
from .risk_adjustment import RiskAdjustment, apply_risk_adjustment
from .score_band import ScoreBand, DEFAULT_SCORE_BANDS, classify_score
from .score_component import DataAvailability, ScoreComponent
from .score_dimension import ScoreDimension, UNIVERSAL_DIMENSIONS
from .score_input import ScoreInput
from .score_result import ScoreResult
from .scoring_model import ScoringModelDefinition, ScoringModelStatus
from .scoring_model_loader import load_registry_from_yaml, model_from_mapping
from .scoring_model_registry import (
    DEFAULT_SCORING_MODEL_REGISTRY,
    ScoringModelRegistry,
)
from .scoring_model_service import ScoringModelSelection, ScoringModelService
from .scoring_profile import ScoringProfile

__all__ = [
    "CompositeDiagnostics",
    "CompositeScore",
    "CompositeScoringEngine",
    "ConfidenceAdjustment",
    "DataAvailability",
    "DEFAULT_NORMALIZATION_REGISTRY",
    "DEFAULT_SCORING_MODEL_REGISTRY",
    "DEFAULT_SCORE_BANDS",
    "DimensionAggregation",
    "NormalizationEngine",
    "NormalizationRegistry",
    "NormalizationResult",
    "RiskAdjustment",
    "ScoreBand",
    "ScoreComponent",
    "ScoreDimension",
    "ScoreInput",
    "ScoreResult",
    "ScoringModelDefinition",
    "ScoringModelRegistry",
    "ScoringModelSelection",
    "ScoringModelService",
    "ScoringModelStatus",
    "ScoringProfile",
    "UNIVERSAL_DIMENSIONS",
    "aggregate_dimension",
    "aggregate_dimensions",
    "apply_confidence_adjustment",
    "apply_risk_adjustment",
    "classify_score",
    "load_registry_from_yaml",
    "model_from_mapping",
]

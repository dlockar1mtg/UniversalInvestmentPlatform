"""Universal scoring contracts and validation utilities."""

from .asset_profile import AssetClassScoringProfile, MetricNormalizationRule
from .asset_profile_loader import (
    asset_profile_from_mapping,
    load_asset_profile,
    load_asset_profiles,
)
from .asset_profile_service import AssetProfileScoringService, MetricObservation
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
from .explanation import (
    AdjustmentExplanation,
    DimensionContribution,
    MissingDataImpact,
    ScoreExplanation,
)
from .explanation_engine import ExplanationEngine
from .explanation_serializer import (
    explanation_to_dict,
    explanation_to_json,
    write_explanation_json,
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
    "AdjustmentExplanation",
    "AssetClassScoringProfile",
    "AssetProfileScoringService",
    "CompositeDiagnostics",
    "CompositeScore",
    "CompositeScoringEngine",
    "ConfidenceAdjustment",
    "DataAvailability",
    "DEFAULT_NORMALIZATION_REGISTRY",
    "DEFAULT_SCORING_MODEL_REGISTRY",
    "DEFAULT_SCORE_BANDS",
    "DimensionAggregation",
    "DimensionContribution",
    "ExplanationEngine",
    "MetricNormalizationRule",
    "MetricObservation",
    "MissingDataImpact",
    "NormalizationEngine",
    "NormalizationRegistry",
    "NormalizationResult",
    "RiskAdjustment",
    "ScoreBand",
    "ScoreComponent",
    "ScoreDimension",
    "ScoreExplanation",
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
    "asset_profile_from_mapping",
    "classify_score",
    "explanation_to_dict",
    "explanation_to_json",
    "load_asset_profile",
    "load_asset_profiles",
    "load_registry_from_yaml",
    "model_from_mapping",
    "write_explanation_json",
]

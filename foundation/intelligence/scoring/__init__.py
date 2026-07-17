"""Universal scoring contracts and validation utilities."""

from .score_band import ScoreBand, DEFAULT_SCORE_BANDS, classify_score
from .score_component import DataAvailability, ScoreComponent
from .score_dimension import ScoreDimension, UNIVERSAL_DIMENSIONS
from .score_input import ScoreInput
from .score_result import ScoreResult
from .scoring_profile import ScoringProfile

__all__ = [
    "DataAvailability",
    "DEFAULT_SCORE_BANDS",
    "ScoreBand",
    "ScoreComponent",
    "ScoreDimension",
    "ScoreInput",
    "ScoreResult",
    "ScoringProfile",
    "UNIVERSAL_DIMENSIONS",
    "classify_score",
]

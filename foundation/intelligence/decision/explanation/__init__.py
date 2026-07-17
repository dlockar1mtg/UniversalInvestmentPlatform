"""Universal fact-based decision explanations."""

from .explanation_engine import UniversalDecisionExplanationEngine
from .explanation_errors import (
    DecisionExplanationError,
    ExplanationConfigurationError,
    ExplanationInputError,
)
from .explanation_profile import ExplanationProfile
from .explanation_result import DecisionExplanation

__all__ = [
    "DecisionExplanation",
    "DecisionExplanationError",
    "ExplanationConfigurationError",
    "ExplanationInputError",
    "ExplanationProfile",
    "UniversalDecisionExplanationEngine",
]

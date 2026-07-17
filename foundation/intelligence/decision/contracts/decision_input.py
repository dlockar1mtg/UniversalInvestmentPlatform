"""Input contract for a universal decision evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .decision_context import DecisionContext
from .decision_errors import DecisionValidationError
from .decision_evidence import DecisionEvidence


@dataclass(frozen=True, slots=True)
class DecisionInput:
    """Standardized intelligence supplied to the decision engine."""

    asset_id: str
    asset_class: str
    time_horizon: str
    context: DecisionContext

    forecast_strength: float
    forecast_confidence: float
    historical_reliability: float
    risk_adjusted_opportunity: float
    market_regime_alignment: float
    diversification_fit: float
    liquidity_quality: float
    valuation_attractiveness: float
    data_quality: float

    evidence: Sequence[DecisionEvidence] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError("asset_id cannot be empty.")

        if not self.asset_class.strip():
            raise DecisionValidationError(
                "asset_class cannot be empty."
            )

        if not self.time_horizon.strip():
            raise DecisionValidationError(
                "time_horizon cannot be empty."
            )

        score_fields = {
            "forecast_strength": self.forecast_strength,
            "forecast_confidence": self.forecast_confidence,
            "historical_reliability": self.historical_reliability,
            "risk_adjusted_opportunity": self.risk_adjusted_opportunity,
            "market_regime_alignment": self.market_regime_alignment,
            "diversification_fit": self.diversification_fit,
            "liquidity_quality": self.liquidity_quality,
            "valuation_attractiveness": self.valuation_attractiveness,
            "data_quality": self.data_quality,
        }

        for name, value in score_fields.items():
            if not 0.0 <= float(value) <= 100.0:
                raise DecisionValidationError(
                    f"{name} must be between 0.0 and 100.0."
                )

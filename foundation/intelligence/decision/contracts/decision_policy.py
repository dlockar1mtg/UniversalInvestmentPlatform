"""Policy contracts governing universal decision evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from .decision_errors import DecisionPolicyError


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Configurable eligibility, confidence, and allocation rules."""

    policy_id: str = "universal-default"
    policy_version: str = "5.1.1"

    minimum_data_quality: float = 60.0
    minimum_forecast_confidence: float = 55.0
    minimum_historical_reliability: float = 50.0
    minimum_liquidity_quality: float = 40.0

    maximum_asset_weight: float = 0.20
    maximum_asset_class_weight: float = 0.50

    strong_buy_threshold: float = 85.0
    buy_threshold: float = 72.0
    accumulate_threshold: float = 62.0
    hold_threshold: float = 50.0
    reduce_threshold: float = 38.0
    sell_threshold: float = 25.0

    allow_negative_available_capital: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise DecisionPolicyError("policy_id cannot be empty.")

        if not self.policy_version.strip():
            raise DecisionPolicyError(
                "policy_version cannot be empty."
            )

        score_fields = {
            "minimum_data_quality": self.minimum_data_quality,
            "minimum_forecast_confidence": (
                self.minimum_forecast_confidence
            ),
            "minimum_historical_reliability": (
                self.minimum_historical_reliability
            ),
            "minimum_liquidity_quality": (
                self.minimum_liquidity_quality
            ),
            "strong_buy_threshold": self.strong_buy_threshold,
            "buy_threshold": self.buy_threshold,
            "accumulate_threshold": self.accumulate_threshold,
            "hold_threshold": self.hold_threshold,
            "reduce_threshold": self.reduce_threshold,
            "sell_threshold": self.sell_threshold,
        }

        for name, value in score_fields.items():
            if not 0.0 <= float(value) <= 100.0:
                raise DecisionPolicyError(
                    f"{name} must be between 0.0 and 100.0."
                )

        for name, value in {
            "maximum_asset_weight": self.maximum_asset_weight,
            "maximum_asset_class_weight": (
                self.maximum_asset_class_weight
            ),
        }.items():
            if not 0.0 <= float(value) <= 1.0:
                raise DecisionPolicyError(
                    f"{name} must be between 0.0 and 1.0."
                )

        thresholds = (
            self.strong_buy_threshold,
            self.buy_threshold,
            self.accumulate_threshold,
            self.hold_threshold,
            self.reduce_threshold,
            self.sell_threshold,
        )

        if list(thresholds) != sorted(thresholds, reverse=True):
            raise DecisionPolicyError(
                "Action thresholds must be ordered from highest to lowest."
            )

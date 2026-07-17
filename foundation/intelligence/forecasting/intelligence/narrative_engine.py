"""Deterministic forecast narrative generation."""

from __future__ import annotations

from ..models import ForecastDirection
from .explainability_contracts import (
    ForecastDriver,
    ForecastRiskFactor,
    HistoricalAnalog,
)


class ForecastNarrativeEngine:
    """Generate concise, deterministic forecast explanations."""

    def generate(
        self,
        *,
        asset_id: str,
        direction: ForecastDirection,
        quality_score: float,
        consensus_score: float,
        calibrated_confidence: float,
        drivers: tuple[ForecastDriver, ...],
        risks: tuple[ForecastRiskFactor, ...],
        analogs: tuple[HistoricalAnalog, ...],
        leading_model: str | None,
    ) -> str:
        direction_text = direction.value.replace("_", " ")
        pieces = [
            (
                f"The {asset_id} forecast is {direction_text} with "
                f"calibrated confidence of {calibrated_confidence:.1%}."
            ),
            (
                f"Historical model quality is {quality_score:.1%}, while "
                f"cross-model consensus is {consensus_score:.1%}."
            ),
        ]

        if leading_model:
            pieces.append(
                f"The ensemble assigns its largest weight to {leading_model}."
            )

        positive = next(
            (item for item in drivers if item.contribution > 0),
            None,
        )
        negative = next(
            (item for item in drivers if item.contribution < 0),
            None,
        )
        if positive:
            pieces.append(
                f"The strongest positive driver is {positive.name}."
            )
        if negative:
            pieces.append(
                f"The strongest negative driver is {negative.name}."
            )

        active_risk = next(
            (item for item in risks if not item.mitigated),
            None,
        )
        if active_risk:
            pieces.append(
                f"The principal risk is {active_risk.name}: "
                f"{active_risk.description}"
            )

        if analogs:
            pieces.append(
                f"The closest historical analog is {analogs[0].label} "
                f"at {analogs[0].similarity_score:.1%} similarity."
            )

        return " ".join(pieces)

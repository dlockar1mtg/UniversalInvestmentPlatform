"""Service for selecting the best historically supported forecast model."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ..models import ForecastHorizon
from .quality_contracts import (
    ForecastModelEvidence,
    ModelSelectionResult,
)
from .ranking_engine import ForecastModelRankingEngine


class ForecastModelSelectionService:
    """Filter, rank, and select a compatible forecast model."""

    def __init__(
        self,
        ranking_engine: ForecastModelRankingEngine | None = None,
    ) -> None:
        self.ranking_engine = ranking_engine or ForecastModelRankingEngine()

    def select(
        self,
        evidence_records: Iterable[ForecastModelEvidence],
        *,
        asset_class: str,
        horizon: ForecastHorizon,
        as_of_date: date | None = None,
    ) -> ModelSelectionResult:
        compatible = tuple(
            evidence
            for evidence in evidence_records
            if evidence.asset_class == asset_class
            and evidence.horizon is horizon
        )

        rankings = self.ranking_engine.rank(
            compatible,
            as_of_date=as_of_date,
        )
        selected = next(
            (entry for entry in rankings if entry.quality.eligible),
            None,
        )

        if not compatible:
            reason = (
                "No historical model evidence matched the requested "
                "asset class and horizon."
            )
        elif selected is None:
            reason = (
                "Compatible evidence was found, but no model met the "
                "quality eligibility requirements."
            )
        else:
            reason = (
                f"Selected {selected.engine_name} "
                f"{selected.engine_version} with adjusted quality "
                f"{selected.quality.adjusted_score:.4f}."
            )

        return ModelSelectionResult(
            asset_class=asset_class,
            horizon=horizon,
            selected=selected,
            rankings=rankings,
            selection_reason=reason,
        )

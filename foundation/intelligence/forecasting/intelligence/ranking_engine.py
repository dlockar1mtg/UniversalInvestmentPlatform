"""Ranking engine for forecast model quality scores."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from .quality_contracts import (
    ForecastModelEvidence,
    ForecastQualityScore,
    ModelRankingEntry,
)
from .quality_engine import ForecastQualityEngine


class ForecastModelRankingEngine:
    """Score and rank compatible model evidence records."""

    def __init__(
        self,
        quality_engine: ForecastQualityEngine | None = None,
    ) -> None:
        self.quality_engine = quality_engine or ForecastQualityEngine()

    def rank(
        self,
        evidence_records: Iterable[ForecastModelEvidence],
        *,
        as_of_date: date | None = None,
        eligible_only: bool = False,
    ) -> tuple[ModelRankingEntry, ...]:
        scores = [
            self.quality_engine.score(
                evidence,
                as_of_date=as_of_date,
            )
            for evidence in evidence_records
        ]

        if eligible_only:
            scores = [score for score in scores if score.eligible]

        scores.sort(key=self._sort_key)

        return tuple(
            ModelRankingEntry(rank=index, quality=score)
            for index, score in enumerate(scores, start=1)
        )

    @staticmethod
    def _sort_key(
        score: ForecastQualityScore,
    ) -> tuple[object, ...]:
        """Sort eligible first, then quality and deterministic tie breakers."""

        evidence = score.evidence
        return (
            not score.eligible,
            -score.adjusted_score,
            -score.raw_score,
            -evidence.sample_size,
            evidence.engine_name,
            evidence.engine_version,
        )

"""Cross-asset validation orchestration."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Iterable

from .cross_asset_contracts import (
    AssetClassValidationSummary,
    CrossAssetValidationReport,
)
from .cross_asset_grading import grade_asset_class


class CrossAssetValidationEngine:
    """Rank asset classes using standardized validation summaries."""

    methodology_version = "1.0.0"

    def compare(
        self,
        summaries: Iterable[AssetClassValidationSummary],
        *,
        horizon_days: int,
    ) -> CrossAssetValidationReport:
        selected = tuple(
            summary
            for summary in summaries
            if summary.horizon_days == horizon_days
        )
        if not selected:
            raise ValueError(
                f"No asset-class summaries found for horizon {horizon_days}."
            )

        provisional = [
            grade_asset_class(summary)
            for summary in selected
        ]
        ranked = sorted(
            provisional,
            key=lambda item: (
                item.adjusted_score,
                item.raw_score,
                item.asset_class,
            ),
            reverse=True,
        )
        final_grades = tuple(
            replace(item, rank=index)
            for index, item in enumerate(ranked, start=1)
        )

        warnings: list[str] = []
        if len(final_grades) < 2:
            warnings.append("Cross-asset comparison contains fewer than two asset classes.")
        if any(item.penalties for item in final_grades):
            warnings.append("One or more grades include coverage or sample-size penalties.")
        if any(item.limitations for item in final_grades):
            warnings.append("Asset-class limitations should be reviewed before interpretation.")

        return CrossAssetValidationReport(
            horizon_days=horizon_days,
            grades=final_grades,
            methodology_version=self.methodology_version,
            warnings=tuple(warnings),
        )

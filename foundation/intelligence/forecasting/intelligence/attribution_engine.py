"""Driver attribution and risk-ranking utilities."""

from __future__ import annotations

from collections.abc import Iterable

from .explainability_contracts import (
    DriverPolarity,
    ForecastDriver,
    ForecastRiskFactor,
)


class ForecastDriverAttributionEngine:
    """Normalize, rank, and classify forecast driver contributions."""

    def attribute(
        self,
        raw_contributions: Iterable[tuple[str, float, str]],
    ) -> tuple[ForecastDriver, ...]:
        items = tuple(raw_contributions)
        if not items:
            return ()

        total_abs = sum(abs(value) for _, value, _ in items)
        if total_abs == 0:
            importance = 1.0 / len(items)
            return tuple(
                ForecastDriver(
                    name=name,
                    contribution=value,
                    importance=importance,
                    polarity=DriverPolarity.NEUTRAL,
                    category=category,
                )
                for name, value, category in sorted(items)
            )

        drivers = [
            ForecastDriver(
                name=name,
                contribution=value,
                importance=abs(value) / total_abs,
                polarity=(
                    DriverPolarity.POSITIVE
                    if value > 0
                    else DriverPolarity.NEGATIVE
                    if value < 0
                    else DriverPolarity.NEUTRAL
                ),
                category=category,
            )
            for name, value, category in items
        ]
        return tuple(
            sorted(
                drivers,
                key=lambda item: (-item.importance, item.name),
            )
        )

    @staticmethod
    def rank_risks(
        risks: Iterable[ForecastRiskFactor],
    ) -> tuple[ForecastRiskFactor, ...]:
        return tuple(
            sorted(
                risks,
                key=lambda item: (
                    item.mitigated,
                    -item.severity,
                    item.name,
                ),
            )
        )

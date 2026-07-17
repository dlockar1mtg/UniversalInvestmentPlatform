"""Stability metrics across horizons and rolling windows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .backtest_dataset import BacktestDataset
from .ranking_metrics import calculate_rank_correlations


@dataclass(frozen=True, slots=True)
class HorizonStabilitySummary:
    """Rank-correlation stability across configured horizons."""

    spearman_by_horizon: Mapping[int, Decimal | None]
    kendall_by_horizon: Mapping[int, Decimal | None]
    mean_spearman: Decimal | None
    minimum_spearman: Decimal | None
    positive_horizon_ratio: Decimal | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "spearman_by_horizon",
            MappingProxyType(dict(self.spearman_by_horizon)),
        )
        object.__setattr__(
            self,
            "kendall_by_horizon",
            MappingProxyType(dict(self.kendall_by_horizon)),
        )


def calculate_horizon_stability(
    dataset: BacktestDataset,
) -> HorizonStabilitySummary:
    spearman: dict[int, Decimal | None] = {}
    kendall: dict[int, Decimal | None] = {}

    for horizon, pairs in dataset.pairs_by_horizon.items():
        result = calculate_rank_correlations(pairs)
        spearman[horizon] = result.spearman
        kendall[horizon] = result.kendall

    valid_spearman = [value for value in spearman.values() if value is not None]
    mean_spearman = (
        sum(valid_spearman, Decimal("0")) / Decimal(len(valid_spearman))
        if valid_spearman
        else None
    )
    minimum_spearman = min(valid_spearman) if valid_spearman else None
    positive_ratio = (
        Decimal(sum(value > 0 for value in valid_spearman))
        / Decimal(len(valid_spearman))
        if valid_spearman
        else None
    )

    return HorizonStabilitySummary(
        spearman_by_horizon=spearman,
        kendall_by_horizon=kendall,
        mean_spearman=mean_spearman,
        minimum_spearman=minimum_spearman,
        positive_horizon_ratio=positive_ratio,
    )

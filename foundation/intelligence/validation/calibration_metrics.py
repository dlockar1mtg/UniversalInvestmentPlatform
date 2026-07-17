"""Score-band and bucket calibration metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Iterable, Mapping
from types import MappingProxyType

from .backtest_dataset import PredictionOutcomePair


@dataclass(frozen=True, slots=True)
class BucketPerformance:
    """Performance summary for one score bucket."""

    bucket_name: str
    observation_count: int
    mean_score: Decimal
    mean_return: Decimal
    median_return: Decimal
    hit_rate: Decimal


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    """Calibration outputs across score bands and quantile buckets."""

    score_bands: Mapping[str, BucketPerformance]
    quantiles: Mapping[str, BucketPerformance]
    calibration_error: Decimal | None
    top_bottom_spread: Decimal | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "score_bands",
            MappingProxyType(dict(self.score_bands)),
        )
        object.__setattr__(
            self,
            "quantiles",
            MappingProxyType(dict(self.quantiles)),
        )


def _bucket_performance(
    name: str,
    pairs: tuple[PredictionOutcomePair, ...],
) -> BucketPerformance:
    scores = [item.prediction.final_score for item in pairs]
    returns = [item.outcome.total_return for item in pairs]
    count = len(pairs)
    return BucketPerformance(
        bucket_name=name,
        observation_count=count,
        mean_score=sum(scores, Decimal("0")) / Decimal(count),
        mean_return=sum(returns, Decimal("0")) / Decimal(count),
        median_return=Decimal(str(median(returns))),
        hit_rate=(
            Decimal(sum(value > 0 for value in returns)) / Decimal(count)
        ),
    )


def performance_by_score_band(
    pairs: Iterable[PredictionOutcomePair],
) -> Mapping[str, BucketPerformance]:
    grouped: dict[str, list[PredictionOutcomePair]] = {}
    for pair in pairs:
        grouped.setdefault(pair.prediction.score_band, []).append(pair)
    return MappingProxyType(
        {
            name: _bucket_performance(name, tuple(rows))
            for name, rows in sorted(grouped.items())
        }
    )


def performance_by_quantile(
    pairs: Iterable[PredictionOutcomePair],
    *,
    quantile_count: int = 5,
) -> Mapping[str, BucketPerformance]:
    pair_tuple = tuple(sorted(
        pairs,
        key=lambda item: item.prediction.final_score,
    ))
    if quantile_count < 2:
        raise ValueError("quantile_count must be at least 2.")
    if not pair_tuple:
        return MappingProxyType({})

    buckets: dict[str, tuple[PredictionOutcomePair, ...]] = {}
    total = len(pair_tuple)
    for index in range(quantile_count):
        start = (index * total) // quantile_count
        end = ((index + 1) * total) // quantile_count
        rows = pair_tuple[start:end]
        if rows:
            name = f"Q{index + 1}"
            buckets[name] = rows

    return MappingProxyType(
        {
            name: _bucket_performance(name, rows)
            for name, rows in buckets.items()
        }
    )


def calculate_calibration_error(
    pairs: Iterable[PredictionOutcomePair],
) -> Decimal | None:
    """Compare normalized score expectation to realized positive-return outcomes."""
    pair_tuple = tuple(pairs)
    if not pair_tuple:
        return None
    absolute_errors = []
    for pair in pair_tuple:
        expected_probability = pair.prediction.final_score / Decimal("100")
        realized = Decimal("1") if pair.outcome.total_return > 0 else Decimal("0")
        absolute_errors.append(abs(expected_probability - realized))
    return sum(absolute_errors, Decimal("0")) / Decimal(len(absolute_errors))


def calculate_calibration_summary(
    pairs: Iterable[PredictionOutcomePair],
    *,
    quantile_count: int = 5,
) -> CalibrationSummary:
    pair_tuple = tuple(pairs)
    bands = performance_by_score_band(pair_tuple)
    quantiles = performance_by_quantile(
        pair_tuple,
        quantile_count=quantile_count,
    )
    top_bottom_spread = None
    if quantiles:
        first = quantiles.get("Q1")
        last = quantiles.get(f"Q{quantile_count}")
        if first is not None and last is not None:
            top_bottom_spread = last.mean_return - first.mean_return

    return CalibrationSummary(
        score_bands=bands,
        quantiles=quantiles,
        calibration_error=calculate_calibration_error(pair_tuple),
        top_bottom_spread=top_bottom_spread,
    )

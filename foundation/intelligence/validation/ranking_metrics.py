"""Ranking metrics for historical validation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Iterable

from .backtest_dataset import PredictionOutcomePair
from .validation import to_decimal


@dataclass(frozen=True, slots=True)
class RankCorrelationResult:
    """Rank-correlation statistics for one prediction/outcome sample."""

    observation_count: int
    spearman: Decimal | None
    kendall: Decimal | None


def _average_ranks(values: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [Decimal("0")] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[position][1]:
            end += 1
        average_rank = (
            Decimal(position + 1) + Decimal(end + 1)
        ) / Decimal("2")
        for index in range(position, end + 1):
            ranks[indexed[index][0]] = average_rank
        position = end + 1
    return tuple(ranks)


def _pearson(x: tuple[Decimal, ...], y: tuple[Decimal, ...]) -> Decimal | None:
    if len(x) != len(y):
        raise ValueError("x and y must have the same length.")
    if len(x) < 2:
        return None

    mean_x = sum(x, Decimal("0")) / Decimal(len(x))
    mean_y = sum(y, Decimal("0")) / Decimal(len(y))
    numerator = sum(
        (a - mean_x) * (b - mean_y)
        for a, b in zip(x, y)
    )
    denominator_x = sum((a - mean_x) ** 2 for a in x)
    denominator_y = sum((b - mean_y) ** 2 for b in y)
    if denominator_x == 0 or denominator_y == 0:
        return None
    return numerator / Decimal(str(sqrt(float(denominator_x * denominator_y))))


def spearman_rank_correlation(
    scores: Iterable[Decimal | int | float | str],
    outcomes: Iterable[Decimal | int | float | str],
) -> Decimal | None:
    """Calculate Spearman rank correlation with average-rank tie handling."""
    score_values = tuple(to_decimal(item, "score") for item in scores)
    outcome_values = tuple(to_decimal(item, "outcome") for item in outcomes)
    if len(score_values) != len(outcome_values):
        raise ValueError("scores and outcomes must have the same length.")
    return _pearson(_average_ranks(score_values), _average_ranks(outcome_values))


def kendall_rank_correlation(
    scores: Iterable[Decimal | int | float | str],
    outcomes: Iterable[Decimal | int | float | str],
) -> Decimal | None:
    """Calculate Kendall tau-a for deterministic pairwise ordering."""
    score_values = tuple(to_decimal(item, "score") for item in scores)
    outcome_values = tuple(to_decimal(item, "outcome") for item in outcomes)
    if len(score_values) != len(outcome_values):
        raise ValueError("scores and outcomes must have the same length.")
    if len(score_values) < 2:
        return None

    concordant = 0
    discordant = 0
    for left in range(len(score_values) - 1):
        for right in range(left + 1, len(score_values)):
            score_diff = score_values[left] - score_values[right]
            outcome_diff = outcome_values[left] - outcome_values[right]
            product = score_diff * outcome_diff
            if product > 0:
                concordant += 1
            elif product < 0:
                discordant += 1

    total_pairs = len(score_values) * (len(score_values) - 1) // 2
    if total_pairs == 0:
        return None
    return Decimal(concordant - discordant) / Decimal(total_pairs)


def calculate_rank_correlations(
    pairs: Iterable[PredictionOutcomePair],
) -> RankCorrelationResult:
    """Calculate score-to-forward-return rank correlations."""
    pair_tuple = tuple(pairs)
    scores = tuple(item.prediction.final_score for item in pair_tuple)
    returns = tuple(item.outcome.total_return for item in pair_tuple)
    return RankCorrelationResult(
        observation_count=len(pair_tuple),
        spearman=spearman_rank_correlation(scores, returns),
        kendall=kendall_rank_correlation(scores, returns),
    )

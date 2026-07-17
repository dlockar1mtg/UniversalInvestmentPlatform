"""Benchmark-relative performance metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Iterable

from .backtest_dataset import PredictionOutcomePair


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonMetrics:
    """Benchmark-relative metrics for a prediction/outcome sample."""

    observation_count: int
    mean_model_return: Decimal | None
    mean_benchmark_return: Decimal | None
    mean_excess_return: Decimal | None
    benchmark_win_rate: Decimal | None
    alpha: Decimal | None
    beta: Decimal | None
    tracking_error: Decimal | None
    information_ratio: Decimal | None
    upside_capture: Decimal | None
    downside_capture: Decimal | None
    relative_max_drawdown: Decimal | None


def _mean(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _sample_std(values: tuple[Decimal, ...]) -> Decimal | None:
    if len(values) < 2:
        return None
    mean = _mean(values)
    assert mean is not None
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
    return Decimal(str(sqrt(float(variance))))


def _covariance(
    x: tuple[Decimal, ...],
    y: tuple[Decimal, ...],
) -> Decimal | None:
    if len(x) != len(y):
        raise ValueError("x and y must have the same length.")
    if len(x) < 2:
        return None
    mean_x = _mean(x)
    mean_y = _mean(y)
    assert mean_x is not None and mean_y is not None
    return sum(
        (a - mean_x) * (b - mean_y)
        for a, b in zip(x, y)
    ) / Decimal(len(x) - 1)


def calculate_beta(
    model_returns: Iterable[Decimal],
    benchmark_returns: Iterable[Decimal],
) -> Decimal | None:
    model = tuple(model_returns)
    benchmark = tuple(benchmark_returns)
    covariance = _covariance(model, benchmark)
    if covariance is None:
        return None
    benchmark_variance = _covariance(benchmark, benchmark)
    if benchmark_variance in (None, Decimal("0")):
        return None
    return covariance / benchmark_variance


def calculate_alpha(
    model_returns: Iterable[Decimal],
    benchmark_returns: Iterable[Decimal],
) -> Decimal | None:
    model = tuple(model_returns)
    benchmark = tuple(benchmark_returns)
    mean_model = _mean(model)
    mean_benchmark = _mean(benchmark)
    beta = calculate_beta(model, benchmark)
    if mean_model is None or mean_benchmark is None or beta is None:
        return None
    return mean_model - beta * mean_benchmark


def calculate_capture_ratio(
    model_returns: Iterable[Decimal],
    benchmark_returns: Iterable[Decimal],
    *,
    positive_benchmark: bool,
) -> Decimal | None:
    selected = [
        (model, benchmark)
        for model, benchmark in zip(model_returns, benchmark_returns)
        if (benchmark > 0 if positive_benchmark else benchmark < 0)
    ]
    if not selected:
        return None
    mean_model = _mean(tuple(item[0] for item in selected))
    mean_benchmark = _mean(tuple(item[1] for item in selected))
    if mean_model is None or mean_benchmark in (None, Decimal("0")):
        return None
    return mean_model / mean_benchmark


def calculate_relative_max_drawdown(
    pairs: Iterable[PredictionOutcomePair],
) -> Decimal | None:
    relative_drawdowns = []
    for pair in pairs:
        if pair.outcome.maximum_drawdown is None:
            continue
        benchmark_return = pair.outcome.benchmark_return
        if benchmark_return is None:
            continue
        relative_drawdowns.append(
            pair.outcome.maximum_drawdown - min(benchmark_return, Decimal("0"))
        )
    return min(relative_drawdowns) if relative_drawdowns else None


def calculate_benchmark_metrics(
    pairs: Iterable[PredictionOutcomePair],
) -> BenchmarkComparisonMetrics:
    valid_pairs = tuple(
        pair
        for pair in pairs
        if pair.outcome.benchmark_return is not None
    )
    if not valid_pairs:
        return BenchmarkComparisonMetrics(
            observation_count=0,
            mean_model_return=None,
            mean_benchmark_return=None,
            mean_excess_return=None,
            benchmark_win_rate=None,
            alpha=None,
            beta=None,
            tracking_error=None,
            information_ratio=None,
            upside_capture=None,
            downside_capture=None,
            relative_max_drawdown=None,
        )

    model_returns = tuple(pair.outcome.total_return for pair in valid_pairs)
    benchmark_returns = tuple(
        pair.outcome.benchmark_return
        for pair in valid_pairs
        if pair.outcome.benchmark_return is not None
    )
    active_returns = tuple(
        model - benchmark
        for model, benchmark in zip(model_returns, benchmark_returns)
    )

    mean_model = _mean(model_returns)
    mean_benchmark = _mean(benchmark_returns)
    mean_excess = _mean(active_returns)
    tracking_error = _sample_std(active_returns)
    information_ratio = (
        mean_excess / tracking_error
        if mean_excess is not None
        and tracking_error not in (None, Decimal("0"))
        else None
    )
    win_rate = (
        Decimal(sum(model > benchmark for model, benchmark in zip(model_returns, benchmark_returns)))
        / Decimal(len(valid_pairs))
    )

    return BenchmarkComparisonMetrics(
        observation_count=len(valid_pairs),
        mean_model_return=mean_model,
        mean_benchmark_return=mean_benchmark,
        mean_excess_return=mean_excess,
        benchmark_win_rate=win_rate,
        alpha=calculate_alpha(model_returns, benchmark_returns),
        beta=calculate_beta(model_returns, benchmark_returns),
        tracking_error=tracking_error,
        information_ratio=information_ratio,
        upside_capture=calculate_capture_ratio(
            model_returns,
            benchmark_returns,
            positive_benchmark=True,
        ),
        downside_capture=calculate_capture_ratio(
            model_returns,
            benchmark_returns,
            positive_benchmark=False,
        ),
        relative_max_drawdown=calculate_relative_max_drawdown(valid_pairs),
    )

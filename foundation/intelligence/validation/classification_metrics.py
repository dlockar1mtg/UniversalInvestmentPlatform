"""Classification-style validation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .backtest_dataset import PredictionOutcomePair


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    """Binary classification metrics derived from score and return thresholds."""

    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    hit_rate: Decimal | None
    precision: Decimal | None
    recall: Decimal | None
    false_positive_rate: Decimal | None
    false_negative_rate: Decimal | None


def _safe_ratio(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return Decimal(numerator) / Decimal(denominator)


def calculate_classification_metrics(
    pairs: Iterable[PredictionOutcomePair],
    *,
    positive_score_threshold: Decimal = Decimal("70"),
    positive_return_threshold: Decimal = Decimal("0"),
) -> ClassificationMetrics:
    """Evaluate whether positive score signals correspond to positive outcomes."""
    tp = fp = tn = fn = 0

    for pair in pairs:
        predicted_positive = pair.prediction.final_score >= positive_score_threshold
        actual_positive = pair.outcome.total_return > positive_return_threshold

        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and not actual_positive:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    return ClassificationMetrics(
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        hit_rate=_safe_ratio(tp + tn, total),
        precision=_safe_ratio(tp, tp + fp),
        recall=_safe_ratio(tp, tp + fn),
        false_positive_rate=_safe_ratio(fp, fp + tn),
        false_negative_rate=_safe_ratio(fn, fn + tp),
    )

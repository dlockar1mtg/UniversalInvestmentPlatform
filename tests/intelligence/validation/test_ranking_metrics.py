from decimal import Decimal

from foundation.intelligence.validation import (
    kendall_rank_correlation,
    spearman_rank_correlation,
)


def test_perfect_positive_spearman() -> None:
    result = spearman_rank_correlation(
        [1, 2, 3, 4],
        [10, 20, 30, 40],
    )
    assert result == Decimal("1")


def test_perfect_negative_spearman() -> None:
    result = spearman_rank_correlation(
        [1, 2, 3, 4],
        [40, 30, 20, 10],
    )
    assert result == Decimal("-1")


def test_perfect_positive_kendall() -> None:
    result = kendall_rank_correlation(
        [1, 2, 3],
        [4, 5, 6],
    )
    assert result == Decimal("1")


def test_perfect_negative_kendall() -> None:
    result = kendall_rank_correlation(
        [1, 2, 3],
        [6, 5, 4],
    )
    assert result == Decimal("-1")

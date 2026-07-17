from decimal import Decimal

import pytest

from foundation.intelligence.scoring import (
    DataAvailability,
    NormalizationEngine,
)
from foundation.intelligence.scoring.strategies import (
    BinaryNormalizer,
    CategoricalNormalizer,
    HigherIsBetterNormalizer,
    LowerIsBetterNormalizer,
    PercentileNormalizer,
    PiecewiseNormalizer,
    TargetCenteredNormalizer,
)


def test_higher_is_better_boundaries_and_midpoint() -> None:
    strategy = HigherIsBetterNormalizer()
    assert strategy.normalize(0, minimum=0, maximum=10).normalized_score == Decimal("0")
    assert strategy.normalize(5, minimum=0, maximum=10).normalized_score == Decimal("50")
    assert strategy.normalize(10, minimum=0, maximum=10).normalized_score == Decimal("100")


def test_higher_is_better_clips_outlier() -> None:
    result = HigherIsBetterNormalizer().normalize(15, minimum=0, maximum=10)
    assert result.normalized_score == Decimal("100")
    assert result.clipped is True


def test_lower_is_better_reverses_scale() -> None:
    strategy = LowerIsBetterNormalizer()
    assert strategy.normalize(0, minimum=0, maximum=10).normalized_score == Decimal("100")
    assert strategy.normalize(10, minimum=0, maximum=10).normalized_score == Decimal("0")


def test_target_centered_scores_target_at_100() -> None:
    strategy = TargetCenteredNormalizer()
    assert strategy.normalize(5, minimum=0, target=5, maximum=10).normalized_score == Decimal("100")
    assert strategy.normalize(0, minimum=0, target=5, maximum=10).normalized_score == Decimal("0")
    assert strategy.normalize(10, minimum=0, target=5, maximum=10).normalized_score == Decimal("0")


def test_percentile_normalization() -> None:
    result = PercentileNormalizer().normalize(3, population=[1, 2, 3, 4, 5])
    assert result.normalized_score == Decimal("50.0")


def test_binary_normalization() -> None:
    strategy = BinaryNormalizer()
    assert strategy.normalize(True).normalized_score == Decimal("100")
    assert strategy.normalize(False).normalized_score == Decimal("0")


def test_binary_rejects_non_bool() -> None:
    with pytest.raises(TypeError):
        BinaryNormalizer().normalize(1)


def test_categorical_case_insensitive_lookup() -> None:
    result = CategoricalNormalizer().normalize(
        "aaa",
        scores={"AAA": 100, "AA": 90},
    )
    assert result.normalized_score == Decimal("100")


def test_piecewise_interpolates() -> None:
    result = PiecewiseNormalizer().normalize(
        5,
        points=[(0, 0), (10, 100)],
    )
    assert result.normalized_score == Decimal("50")


def test_engine_preserves_missing_data_state() -> None:
    result = NormalizationEngine().normalize(
        "higher_is_better",
        None,
        availability=DataAvailability.UNAVAILABLE,
        minimum=0,
        maximum=10,
    )
    assert result.normalized_score is None
    assert result.availability is DataAvailability.UNAVAILABLE


def test_engine_rejects_unknown_strategy() -> None:
    with pytest.raises(KeyError):
        NormalizationEngine().normalize("does_not_exist", 1)


def test_non_clipping_mode_rejects_outlier() -> None:
    with pytest.raises(ValueError):
        HigherIsBetterNormalizer().normalize(
            11,
            minimum=0,
            maximum=10,
            clip=False,
        )

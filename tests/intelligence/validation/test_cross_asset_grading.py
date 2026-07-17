from decimal import Decimal

from foundation.intelligence.validation import (
    AssetClassValidationSummary,
    grade_asset_class,
)


def summary(**overrides):
    data = {
        "asset_class": "crypto",
        "model_id": "crypto_core_v1",
        "model_version": "1.0.0",
        "horizon_days": 365,
        "observation_count": 250,
        "asset_count": 10,
        "coverage_ratio": Decimal("0.95"),
        "spearman": Decimal("0.40"),
        "kendall": Decimal("0.30"),
        "hit_rate": Decimal("0.65"),
        "top_bottom_spread": Decimal("0.12"),
        "mean_excess_return": Decimal("0.05"),
        "information_ratio": Decimal("0.80"),
        "benchmark_win_rate": Decimal("0.60"),
        "calibration_error": Decimal("0.20"),
        "limitations": (),
    }
    data.update(overrides)
    return AssetClassValidationSummary(**data)


def test_grade_asset_class_produces_grade() -> None:
    grade = grade_asset_class(summary())
    assert grade.adjusted_score > Decimal("0")
    assert grade.grade in {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"}


def test_low_coverage_applies_penalty() -> None:
    grade = grade_asset_class(summary(coverage_ratio=Decimal("0.50")))
    assert "coverage" in grade.penalties
    assert grade.adjusted_score < grade.raw_score


def test_small_sample_applies_penalties() -> None:
    grade = grade_asset_class(
        summary(observation_count=20, asset_count=2)
    )
    assert "sample_size" in grade.penalties
    assert "asset_breadth" in grade.penalties

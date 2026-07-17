from decimal import Decimal

from foundation.intelligence.validation import (
    AssetClassValidationSummary,
    ValidationProfile,
    evaluate_model_certification,
)


def summary():
    return AssetClassValidationSummary(
        asset_class="crypto",
        model_id="crypto_core_v1",
        model_version="1.0.0",
        horizon_days=365,
        observation_count=200,
        asset_count=10,
        coverage_ratio=Decimal("0.95"),
        spearman=Decimal("0.30"),
        kendall=Decimal("0.20"),
        hit_rate=Decimal("0.60"),
        top_bottom_spread=Decimal("0.10"),
        mean_excess_return=Decimal("0.04"),
        information_ratio=Decimal("0.60"),
        benchmark_win_rate=Decimal("0.58"),
        calibration_error=Decimal("0.20"),
    )


def profile():
    return ValidationProfile(
        profile_id="baseline_v1",
        version="1.0.0",
        minimum_observations=100,
        minimum_assets=5,
        minimum_date_coverage=Decimal("0.80"),
        rank_metrics=("spearman_rank_correlation",),
        performance_metrics=("hit_rate",),
        thresholds={
            "spearman_rank_correlation": Decimal("0.10"),
            "top_bottom_spread": Decimal("0.00"),
            "hit_rate": Decimal("0.50"),
        },
    )


def test_model_certification_passes_thresholds() -> None:
    decision = evaluate_model_certification(summary(), profile())
    assert decision.passed is True
    assert all(item.passed for item in decision.evaluations.values())


def test_model_certification_fails_sample_requirement() -> None:
    base = summary()
    low_sample = AssetClassValidationSummary(
        asset_class=base.asset_class,
        model_id=base.model_id,
        model_version=base.model_version,
        horizon_days=base.horizon_days,
        observation_count=20,
        asset_count=base.asset_count,
        coverage_ratio=base.coverage_ratio,
        spearman=base.spearman,
        kendall=base.kendall,
        hit_rate=base.hit_rate,
        top_bottom_spread=base.top_bottom_spread,
        mean_excess_return=base.mean_excess_return,
        information_ratio=base.information_ratio,
        benchmark_win_rate=base.benchmark_win_rate,
        calibration_error=base.calibration_error,
        limitations=base.limitations,
    )
    decision = evaluate_model_certification(low_sample, profile())
    assert decision.passed is False
    assert decision.evaluations["minimum_observations"].passed is False

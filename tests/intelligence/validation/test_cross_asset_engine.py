from decimal import Decimal

from foundation.intelligence.validation import (
    AssetClassValidationSummary,
    CrossAssetValidationEngine,
)


def summary(asset_class: str, spearman: str, excess: str):
    return AssetClassValidationSummary(
        asset_class=asset_class,
        model_id=f"{asset_class}_model",
        model_version="1.0.0",
        horizon_days=365,
        observation_count=200,
        asset_count=10,
        coverage_ratio=Decimal("0.95"),
        spearman=Decimal(spearman),
        kendall=Decimal("0.20"),
        hit_rate=Decimal("0.60"),
        top_bottom_spread=Decimal("0.08"),
        mean_excess_return=Decimal(excess),
        information_ratio=Decimal("0.60"),
        benchmark_win_rate=Decimal("0.58"),
        calibration_error=Decimal("0.20"),
    )


def test_cross_asset_engine_ranks_assets() -> None:
    report = CrossAssetValidationEngine().compare(
        (
            summary("crypto", "0.40", "0.05"),
            summary("etf", "0.25", "0.02"),
            summary("metals", "0.10", "0.01"),
        ),
        horizon_days=365,
    )
    assert [item.rank for item in report.grades] == [1, 2, 3]
    assert report.grades[0].adjusted_score >= report.grades[1].adjusted_score


def test_cross_asset_engine_filters_horizon() -> None:
    report = CrossAssetValidationEngine().compare(
        (summary("crypto", "0.40", "0.05"),),
        horizon_days=365,
    )
    assert report.horizon_days == 365
    assert len(report.grades) == 1

from decimal import Decimal

from foundation.intelligence.validation import (
    AssetClassValidationSummary,
    CrossAssetValidationEngine,
    ValidationProfile,
    build_dashboard_dataset,
    build_executive_report,
    evaluate_model_certification,
)


def summary(asset_class: str, spearman: str):
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
        mean_excess_return=Decimal("0.03"),
        information_ratio=Decimal("0.50"),
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


def test_executive_report_and_dashboard_dataset() -> None:
    summaries = (
        summary("crypto", "0.40"),
        summary("etf", "0.25"),
    )
    cross_asset = CrossAssetValidationEngine().compare(
        summaries,
        horizon_days=365,
    )
    decisions = {
        item.asset_class: evaluate_model_certification(item, profile())
        for item in summaries
    }
    report = build_executive_report(cross_asset, decisions)
    assert report.overall_status == "certified"
    assert len(report.scorecards) == 2

    dataset = build_dashboard_dataset(report)
    assert dataset.summary_kpis["asset_class_count"] == 2
    assert dataset.summary_kpis["certified_model_count"] == 2

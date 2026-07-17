import csv
import json
from decimal import Decimal

from foundation.intelligence.validation import (
    AssetClassValidationSummary,
    CrossAssetValidationEngine,
    ValidationProfile,
    build_executive_report,
    evaluate_model_certification,
    executive_report_to_json,
    write_scorecards_csv,
)


def build_report():
    summary = AssetClassValidationSummary(
        asset_class="crypto",
        model_id="crypto_model",
        model_version="1.0.0",
        horizon_days=365,
        observation_count=200,
        asset_count=10,
        coverage_ratio=Decimal("0.95"),
        spearman=Decimal("0.40"),
        kendall=Decimal("0.30"),
        hit_rate=Decimal("0.65"),
        top_bottom_spread=Decimal("0.10"),
        mean_excess_return=Decimal("0.04"),
        information_ratio=Decimal("0.60"),
        benchmark_win_rate=Decimal("0.60"),
        calibration_error=Decimal("0.20"),
    )
    profile = ValidationProfile(
        profile_id="baseline",
        version="1.0.0",
        minimum_observations=100,
        minimum_assets=5,
        minimum_date_coverage=Decimal("0.80"),
        rank_metrics=("spearman_rank_correlation",),
        performance_metrics=("hit_rate",),
        thresholds={
            "spearman_rank_correlation": Decimal("0.10"),
            "top_bottom_spread": Decimal("0"),
            "hit_rate": Decimal("0.50"),
        },
    )
    cross_asset = CrossAssetValidationEngine().compare(
        (summary,),
        horizon_days=365,
    )
    decision = evaluate_model_certification(summary, profile)
    return build_executive_report(
        cross_asset,
        {"crypto": decision},
    )


def test_json_serialization_is_valid() -> None:
    payload = executive_report_to_json(build_report())
    parsed = json.loads(payload)
    assert parsed["overall_status"] == "certified"


def test_csv_export(tmp_path) -> None:
    path = write_scorecards_csv(
        build_report(),
        tmp_path / "scorecards.csv",
    )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["asset_class"] == "crypto"

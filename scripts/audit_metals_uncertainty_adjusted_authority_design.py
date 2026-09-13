"""Read-only design audit for a future UIP-native Metals uncertainty-adjusted authority."""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import psycopg

EXPECTED_NATIVE_CYCLE_STATUS = "PASS"
EXPECTED_MODEL_ID = "uip-metals-native-trend-v1"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage-evidence", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--regime-probability-manifest", type=Path, required=True)
    parser.add_argument("--risk-manifest", type=Path, required=True)
    parser.add_argument("--recommendation-change-manifest", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    native_cycle = read_json(args.native_cycle)
    regime = read_json(args.regime_probability_manifest)
    risk = read_json(args.risk_manifest)
    recommendation_change = read_json(args.recommendation_change_manifest)
    methodology = read_json(args.methodology)

    restored = ((lineage.get("record_types") or {}).get("metals_uncertainty_adjusted") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(v) for v in restored.get("payload_keys", []))

    models = methodology.get("models") or []
    model = models[0] if models and isinstance(models[0], dict) else {}
    registry_version = str(methodology.get("registry_version", ""))
    registry_model_id = str(model.get("model_id", ""))

    forecasts = native_cycle.get("forecasts") or []
    by_asset: dict[str, list[dict]] = defaultdict(list)
    horizons: set[int] = set()
    model_ids: set[str] = set()
    methodology_versions: set[str] = set()
    confidence_values: list[float] = []
    expected_returns: list[float] = []
    for row in forecasts:
        asset = str(row.get("asset_id", "")).strip()
        if asset:
            by_asset[asset].append(row)
        if row.get("horizon_months") is not None:
            horizons.add(int(row["horizon_months"]))
        model_ids.add(str(row.get("model_id", "")))
        methodology_versions.add(str(row.get("methodology_version", "")))
        if row.get("confidence") is not None:
            confidence_values.append(float(row["confidence"]))
        if row.get("expected_return") is not None:
            expected_returns.append(float(row["expected_return"]))

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    with psycopg.connect(dsn) as db:
        with db.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT series_id), COUNT(DISTINCT observation_date),
                       MIN(observation_date), MAX(observation_date)
                FROM metals_observations
                """
            )
            benchmark_row_count, benchmark_series_count, benchmark_date_count, benchmark_first, benchmark_last = cur.fetchone()
            cur.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT ticker), COUNT(DISTINCT observation_date),
                       MIN(observation_date), MAX(observation_date)
                FROM metals_vehicle_observations
                """
            )
            vehicle_row_count, vehicle_series_count, vehicle_date_count, vehicle_first, vehicle_last = cur.fetchone()
            db.rollback()

    checks = {
        "restored_uncertainty_adjusted_family_present": restored_count > 0,
        "restored_uncertainty_adjusted_schema_observed": len(restored_keys) > 0,
        "native_cycle_pass": native_cycle.get("status") == EXPECTED_NATIVE_CYCLE_STATUS,
        "native_cycle_has_forecasts": len(forecasts) > 0,
        "native_cycle_has_multiple_assets": len(by_asset) > 1,
        "native_cycle_has_multiple_horizons": len(horizons) > 1,
        "native_cycle_model_id_matches_registry": model_ids == {registry_model_id} == {EXPECTED_MODEL_ID},
        "native_cycle_methodology_version_matches_registry": methodology_versions == {registry_version},
        "native_cycle_confidence_complete": len(confidence_values) == len(forecasts),
        "native_cycle_expected_return_complete": len(expected_returns) == len(forecasts),
        "regime_probability_authority_pass": regime.get("status") == "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS",
        "regime_probability_authority_nonlegacy": regime.get("legacy_equivalent") is False,
        "regime_probability_asset_count_matches_native_cycle": int(regime.get("asset_count", -1)) == len(by_asset),
        "regime_probability_is_not_claimed_calibrated": regime.get("statistical_calibration_claimed") is False,
        "risk_authority_pass": risk.get("status") == "METALS_NATIVE_RISK_V1_PASS",
        "risk_authority_nonlegacy": risk.get("legacy_equivalent") is False,
        "risk_scope_is_vehicle_only": risk.get("scope") == "VEHICLE_ONLY",
        "recommendation_change_authority_pass": recommendation_change.get("status") == "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS",
        "recommendation_change_authority_nonlegacy": recommendation_change.get("legacy_equivalent") is False,
        "benchmark_history_has_multiple_dates": int(benchmark_date_count) > 1,
        "benchmark_history_has_multiple_series": int(benchmark_series_count) > 1,
        "vehicle_history_has_multiple_dates": int(vehicle_date_count) > 1,
        "vehicle_history_has_multiple_series": int(vehicle_series_count) > 1,
    }

    design_ready = all(checks.values())
    decision = (
        "AUTHORIZE_UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1_DESIGN"
        if design_ready
        else "DO_NOT_AUTHORIZE_UNCERTAINTY_ADJUSTED_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED"
    )

    evidence = {
        "status": "METALS_UNCERTAINTY_ADJUSTED_AUTHORITY_DESIGN_AUDIT_PASS" if design_ready else "METALS_UNCERTAINTY_ADJUSTED_AUTHORITY_DESIGN_AUDIT_FAIL_CLOSED",
        "decision": decision,
        "query_policy": "READ_ONLY_SELECT_ONLY",
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_uncertainty_adjusted": {
            "row_count": restored_count,
            "payload_keys": restored_keys,
            "distinct_standard_lineage": restored.get("distinct_standard_lineage", []),
        },
        "native_current_authority": {
            "status": native_cycle.get("status"),
            "forecast_count": len(forecasts),
            "asset_count": len(by_asset),
            "horizons_months": sorted(horizons),
            "model_ids": sorted(model_ids),
            "methodology_versions": sorted(methodology_versions),
            "confidence_count": len(confidence_values),
            "expected_return_count": len(expected_returns),
        },
        "supporting_native_authorities": {
            "regime_probability": {
                "status": regime.get("status"),
                "authority_id": regime.get("authority_id"),
                "asset_count": regime.get("asset_count"),
                "row_count": regime.get("row_count"),
                "probability_interpretation": regime.get("probability_interpretation"),
                "statistical_calibration_claimed": regime.get("statistical_calibration_claimed"),
            },
            "risk": {
                "status": risk.get("status"),
                "authority_id": risk.get("authority_id"),
                "scope": risk.get("scope"),
                "vehicle_count": risk.get("vehicle_count"),
                "row_count": risk.get("row_count"),
            },
            "recommendation_change": {
                "status": recommendation_change.get("status"),
                "authority_id": recommendation_change.get("authority_id"),
                "scope": recommendation_change.get("scope"),
                "change_row_count": recommendation_change.get("change_row_count"),
                "latest_state_parity": recommendation_change.get("latest_state_parity"),
            },
        },
        "native_history_authority": {
            "benchmark_row_count": int(benchmark_row_count),
            "benchmark_series_count": int(benchmark_series_count),
            "benchmark_distinct_date_count": int(benchmark_date_count),
            "benchmark_first_date": str(benchmark_first),
            "benchmark_last_date": str(benchmark_last),
            "vehicle_row_count": int(vehicle_row_count),
            "vehicle_series_count": int(vehicle_series_count),
            "vehicle_distinct_date_count": int(vehicle_date_count),
            "vehicle_first_date": str(vehicle_first),
            "vehicle_last_date": str(vehicle_last),
        },
        "checks": checks,
        "candidate_authority_boundary": "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON",
        "missing_semantics_to_govern_before_builder": [
            "exact uncertainty-adjusted quantity: adjusted expected return, adjusted projected value, interval, score, or explicitly versioned combination",
            "one-row grain and whether every commodity-horizon forecast must produce exactly one adjusted row",
            "uncertainty source definition and prohibition on treating native confidence as a statistically calibrated interval without evidence",
            "whether and how regime support may modify uncertainty without double-counting native confidence",
            "whether vehicle-only Risk V1 can contribute and, if so, the explicit governed vehicle-to-commodity mapping; absent that mapping, risk contribution must remain prohibited",
            "penalty or shrinkage formula, parameter bounds, monotonicity requirements, and zero/negative expected-return behavior",
            "relationship between 12, 36, and 60 month horizons and whether adjustment parameters are horizon-specific",
            "minimum evidence/completeness thresholds and unavailable-state behavior",
            "historical as-of reconstruction policy, cadence, and temporal cutoff if historical adjusted views are ever produced",
            "same-date source revision policy for any historical inputs used by the authority",
            "methodology-version transition policy and exact source-authority hashes or identifiers required for reproducibility",
            "explicit prohibition on copying the restored 32 uncertainty-adjusted rows forward as fresh authority",
            "explicit prohibition on cross-asset ranking, portfolio allocation, or execution semantics in R1",
        ],
        "notes": [
            "Design authorization does not authorize production uncertainty-adjusted rows.",
            "The 32 restored uncertainty-adjusted rows are historical evidence only; their row count, formulas, and asset/horizon grain do not define the new authority.",
            "Current UIP-native forecasts provide expected return and confidence; Regime Probability V1 provides descriptive normalized regime support; Risk V1 remains vehicle-only.",
            "A V1 authority must remain legacy_equivalent=false and must not silently map vehicle risk to commodity forecasts.",
            "No statistically calibrated uncertainty interval may be claimed unless calibration is explicitly implemented and certified.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print(f"METALS_UNCERTAINTY_ADJUSTED_AUTHORITY_DESIGN={decision}")
    return 0 if design_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

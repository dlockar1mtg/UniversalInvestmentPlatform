"""Read-only design audit for a future UIP-native Metals recommendation-change authority."""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import psycopg

EXPECTED_NATIVE_CYCLE_STATUS = "PASS"
EXPECTED_MODEL_ID = "uip-metals-native-trend-v1"
EXPECTED_RECOMMENDATIONS = {"STRONG_BUY", "BUY", "HOLD", "REDUCE", "AVOID"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage-evidence", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    native_cycle = read_json(args.native_cycle)
    methodology = read_json(args.methodology)

    restored = ((lineage.get("record_types") or {}).get("metals_recommendation_change") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(v) for v in restored.get("payload_keys", []))

    models = methodology.get("models") or []
    model = models[0] if models and isinstance(models[0], dict) else {}
    policy = model.get("recommendation_policy") or {}
    registry_version = str(methodology.get("registry_version", ""))
    model_id = str(model.get("model_id", ""))

    forecasts = native_cycle.get("forecasts") or []
    by_asset: dict[str, set[str]] = defaultdict(set)
    horizons: set[int] = set()
    model_ids: set[str] = set()
    methodology_versions: set[str] = set()
    for row in forecasts:
        asset = str(row.get("asset_id", "")).strip()
        recommendation = str(row.get("recommendation", "")).strip()
        if asset:
            by_asset[asset].add(recommendation)
        if row.get("horizon_months") is not None:
            horizons.add(int(row["horizon_months"]))
        model_ids.add(str(row.get("model_id", "")))
        methodology_versions.add(str(row.get("methodology_version", "")))

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

    thresholds = [
        policy.get("strong_buy_min_return"),
        policy.get("buy_min_return"),
        policy.get("hold_min_return"),
        policy.get("reduce_min_return"),
    ]
    threshold_values = [float(v) for v in thresholds if v is not None]
    policy_ordered = len(threshold_values) == 4 and threshold_values == sorted(threshold_values, reverse=True)
    actual_recommendations = {value for values in by_asset.values() for value in values}

    checks = {
        "restored_recommendation_change_family_present": restored_count > 0,
        "restored_recommendation_change_schema_observed": len(restored_keys) > 0,
        "native_cycle_pass": native_cycle.get("status") == EXPECTED_NATIVE_CYCLE_STATUS,
        "native_cycle_has_forecasts": len(forecasts) > 0,
        "native_cycle_has_multiple_assets": len(by_asset) > 1,
        "native_cycle_recommendations_governed": bool(actual_recommendations) and actual_recommendations <= EXPECTED_RECOMMENDATIONS,
        "native_cycle_asset_recommendation_consistent_across_horizons": all(len(values) == 1 for values in by_asset.values()),
        "native_cycle_model_id_matches_registry": model_ids == {model_id} == {EXPECTED_MODEL_ID},
        "native_cycle_methodology_version_matches_registry": methodology_versions == {registry_version},
        "recommendation_policy_complete_and_ordered": policy_ordered and str(policy.get("otherwise", "")) == "AVOID",
        "benchmark_history_has_multiple_dates": int(benchmark_date_count) > 1,
        "benchmark_history_has_multiple_series": int(benchmark_series_count) > 1,
        "vehicle_history_has_multiple_dates": int(vehicle_date_count) > 1,
        "vehicle_history_has_multiple_series": int(vehicle_series_count) > 1,
    }

    design_ready = all(checks.values())
    decision = (
        "AUTHORIZE_UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1_DESIGN"
        if design_ready
        else "DO_NOT_AUTHORIZE_RECOMMENDATION_CHANGE_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED"
    )

    evidence = {
        "status": "METALS_RECOMMENDATION_CHANGE_AUTHORITY_DESIGN_AUDIT_PASS" if design_ready else "METALS_RECOMMENDATION_CHANGE_AUTHORITY_DESIGN_AUDIT_FAIL_CLOSED",
        "decision": decision,
        "query_policy": "READ_ONLY_SELECT_ONLY",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_recommendation_change": {
            "row_count": restored_count,
            "payload_keys": restored_keys,
            "distinct_standard_lineage": restored.get("distinct_standard_lineage", []),
        },
        "native_current_authority": {
            "status": native_cycle.get("status"),
            "forecast_count": len(forecasts),
            "asset_count": len(by_asset),
            "horizons_months": sorted(horizons),
            "recommendations": sorted(actual_recommendations),
            "model_ids": sorted(model_ids),
            "methodology_versions": sorted(methodology_versions),
            "recommendation_policy": policy,
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
        "candidate_authority_boundary": "BENCHMARK_COMMODITY_ASSET_ONLY",
        "missing_semantics_to_govern_before_builder": [
            "canonical recommendation-change output schema",
            "historical as-of evaluation cadence and temporal cutoff rule",
            "change event grain: one row per commodity transition rather than per forecast horizon",
            "first-observation behavior: no event versus explicit initial-state event",
            "same-day source revision and ordering policy",
            "methodology-version transition policy across historical reconstruction",
            "whether no-op repeated recommendations are omitted or emitted",
            "explicit prohibition on commodity-to-vehicle recommendation projection",
        ],
        "notes": [
            "Design authorization does not authorize production recommendation-change rows.",
            "The current native cycle publishes only latest forecast state; historical changes must be reconstructed from persisted native observations under governed temporal semantics.",
            "Restored recommendation-change rows are evidence only and must not be copied forward as fresh.",
            "Any V1 authority must remain legacy_equivalent=false and commodity-level unless separately governed vehicle recommendation authority exists.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print(f"METALS_RECOMMENDATION_CHANGE_AUTHORITY_DESIGN={decision}")
    return 0 if design_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

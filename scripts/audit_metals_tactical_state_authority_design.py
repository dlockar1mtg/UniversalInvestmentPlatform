"""Read-only design audit for a future UIP-native Metals tactical-state authority."""
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
    parser.add_argument("--regime-probability-manifest", type=Path, required=True)
    parser.add_argument("--uncertainty-adjusted-manifest", type=Path, required=True)
    parser.add_argument("--risk-manifest", type=Path, required=True)
    parser.add_argument("--recommendation-change-manifest", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    native_cycle = read_json(args.native_cycle)
    regime = read_json(args.regime_probability_manifest)
    uncertainty = read_json(args.uncertainty_adjusted_manifest)
    risk = read_json(args.risk_manifest)
    recommendation_change = read_json(args.recommendation_change_manifest)
    methodology = read_json(args.methodology)

    restored = ((lineage.get("record_types") or {}).get("tactical_state") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(v) for v in restored.get("payload_keys", []))

    models = methodology.get("models") or []
    model = models[0] if models and isinstance(models[0], dict) else {}
    policy = model.get("recommendation_policy") or {}
    registry_version = str(methodology.get("registry_version", ""))
    registry_model_id = str(model.get("model_id", ""))

    forecasts = native_cycle.get("forecasts") or []
    by_asset: dict[str, set[str]] = defaultdict(set)
    horizons: set[int] = set()
    model_ids: set[str] = set()
    methodology_versions: set[str] = set()
    confidence_count = 0
    expected_return_count = 0
    for row in forecasts:
        asset = str(row.get("asset_id", "")).strip()
        recommendation = str(row.get("recommendation", "")).strip()
        if asset:
            by_asset[asset].add(recommendation)
        if row.get("horizon_months") is not None:
            horizons.add(int(row["horizon_months"]))
        model_ids.add(str(row.get("model_id", "")))
        methodology_versions.add(str(row.get("methodology_version", "")))
        if row.get("confidence") is not None:
            confidence_count += 1
        if row.get("expected_return") is not None:
            expected_return_count += 1

    actual_recommendations = {value for values in by_asset.values() for value in values}

    thresholds = [
        policy.get("strong_buy_min_return"),
        policy.get("buy_min_return"),
        policy.get("hold_min_return"),
        policy.get("reduce_min_return"),
    ]
    threshold_values = [float(v) for v in thresholds if v is not None]
    policy_ordered = len(threshold_values) == 4 and threshold_values == sorted(threshold_values, reverse=True)

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
        "restored_tactical_state_family_present": restored_count > 0,
        "restored_tactical_state_schema_observed": len(restored_keys) > 0,
        "native_cycle_pass": native_cycle.get("status") == EXPECTED_NATIVE_CYCLE_STATUS,
        "native_cycle_has_forecasts": len(forecasts) > 0,
        "native_cycle_has_multiple_assets": len(by_asset) > 1,
        "native_cycle_has_multiple_horizons": len(horizons) > 1,
        "native_cycle_recommendations_governed": bool(actual_recommendations) and actual_recommendations <= EXPECTED_RECOMMENDATIONS,
        "native_cycle_asset_recommendation_consistent_across_horizons": all(len(values) == 1 for values in by_asset.values()),
        "native_cycle_model_id_matches_registry": model_ids == {registry_model_id} == {EXPECTED_MODEL_ID},
        "native_cycle_methodology_version_matches_registry": methodology_versions == {registry_version},
        "native_cycle_confidence_complete": confidence_count == len(forecasts),
        "native_cycle_expected_return_complete": expected_return_count == len(forecasts),
        "recommendation_policy_complete_and_ordered": policy_ordered and str(policy.get("otherwise", "")) == "AVOID",
        "regime_probability_authority_pass": regime.get("status") == "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS",
        "regime_probability_authority_nonlegacy": regime.get("legacy_equivalent") is False,
        "regime_probability_scope_is_commodity_only": regime.get("scope") == "BENCHMARK_COMMODITY_ASSET_ONLY",
        "uncertainty_adjusted_authority_pass": uncertainty.get("status") == "METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1_PASS",
        "uncertainty_adjusted_authority_nonlegacy": uncertainty.get("legacy_equivalent") is False,
        "uncertainty_adjusted_scope_is_commodity_horizon": uncertainty.get("scope") == "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON",
        "risk_authority_pass": risk.get("status") == "METALS_NATIVE_RISK_V1_PASS",
        "risk_authority_nonlegacy": risk.get("legacy_equivalent") is False,
        "risk_scope_is_vehicle_only": risk.get("scope") == "VEHICLE_ONLY",
        "recommendation_change_authority_pass": recommendation_change.get("status") == "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS",
        "recommendation_change_authority_nonlegacy": recommendation_change.get("legacy_equivalent") is False,
        "recommendation_change_scope_is_commodity_only": recommendation_change.get("scope") == "BENCHMARK_COMMODITY_ASSET_ONLY",
        "benchmark_history_has_multiple_dates": int(benchmark_date_count) > 1,
        "benchmark_history_has_multiple_series": int(benchmark_series_count) > 1,
        "vehicle_history_has_multiple_dates": int(vehicle_date_count) > 1,
        "vehicle_history_has_multiple_series": int(vehicle_series_count) > 1,
    }

    design_ready = all(checks.values())
    decision = (
        "AUTHORIZE_UIP_NATIVE_METALS_TACTICAL_STATE_V1_DESIGN"
        if design_ready
        else "DO_NOT_AUTHORIZE_TACTICAL_STATE_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED"
    )

    evidence = {
        "status": "METALS_TACTICAL_STATE_AUTHORITY_DESIGN_AUDIT_PASS" if design_ready else "METALS_TACTICAL_STATE_AUTHORITY_DESIGN_AUDIT_FAIL_CLOSED",
        "decision": decision,
        "query_policy": "READ_ONLY_SELECT_ONLY",
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_tactical_state": {
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
        "supporting_native_authorities": {
            "regime_probability": {
                "status": regime.get("status"),
                "authority_id": regime.get("authority_id"),
                "scope": regime.get("scope"),
                "probability_interpretation": regime.get("probability_interpretation"),
                "statistical_calibration_claimed": regime.get("statistical_calibration_claimed"),
            },
            "uncertainty_adjusted": {
                "status": uncertainty.get("status"),
                "authority_id": uncertainty.get("authority_id"),
                "scope": uncertainty.get("scope"),
                "adjusted_quantity": uncertainty.get("adjusted_quantity"),
                "adjustment_interpretation": uncertainty.get("adjustment_interpretation"),
            },
            "risk": {
                "status": risk.get("status"),
                "authority_id": risk.get("authority_id"),
                "scope": risk.get("scope"),
                "vehicle_count": risk.get("vehicle_count"),
            },
            "recommendation_change": {
                "status": recommendation_change.get("status"),
                "authority_id": recommendation_change.get("authority_id"),
                "scope": recommendation_change.get("scope"),
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
        "candidate_authority_boundary": "UNRESOLVED_SCOPE_REQUIRES_EXPLICIT_GOVERNANCE_BEFORE_BUILDER",
        "scope_options_requiring_explicit_choice": [
            "BENCHMARK_COMMODITY_ASSET_ONLY using certified commodity recommendation/regime/uncertainty authorities",
            "VEHICLE_ONLY using certified vehicle observation/risk authorities",
            "SEPARATE_COMMODITY_AND_VEHICLE_AUTHORITIES with no implicit projection between them",
        ],
        "missing_semantics_to_govern_before_builder": [
            "canonical subject boundary: commodity, vehicle, or two separately versioned authorities",
            "canonical tactical-state taxonomy and exact meaning of every state",
            "whether tactical state is descriptive context or an action recommendation; no execution semantics may be implied",
            "exact mapping, if any, from STRONG_BUY/BUY/HOLD/REDUCE/AVOID into tactical states",
            "whether descriptive Regime Probability V1 may affect state assignment and how confidence double-counting is prevented",
            "whether Uncertainty Adjusted V1 may affect state assignment and the exact threshold semantics",
            "vehicle-only Risk V1 contribution rules; no vehicle-to-commodity projection without separately governed mapping",
            "horizon policy: current state, one selected horizon, multi-horizon consensus, or explicit horizon-specific states",
            "minimum evidence/completeness thresholds and unavailable-state behavior; missing authority must remain missing rather than defaulting to HOLD or WAIT",
            "historical as-of reconstruction policy and temporal cutoff if tactical-state history is ever produced",
            "same-date source revision policy for any historical inputs used by the authority",
            "methodology-version transition policy and exact source-authority hashes or identifiers required for reproducibility",
            "explicit prohibition on copying restored tactical-state rows, action mappings, or classifier outputs forward as fresh authority",
            "explicit prohibition on cross-asset ranking, portfolio allocation, trade sizing, or automatic execution in V1",
        ],
        "notes": [
            "Design authorization does not authorize production tactical-state rows.",
            "The restored tactical-state family is historical evidence only and cannot define the new taxonomy, action mapping, scope, or classifier by inheritance.",
            "Current UIP-native commodity recommendations are governed, while Risk V1 remains vehicle-only; those subject boundaries must not be silently merged.",
            "A V1 authority must remain legacy_equivalent=false and preserve missing-as-missing behavior.",
            "No vehicle tactical context may be presented as commodity tactical state unless an explicit governed mapping is separately certified.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print(f"METALS_TACTICAL_STATE_AUTHORITY_DESIGN={decision}")
    return 0 if design_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

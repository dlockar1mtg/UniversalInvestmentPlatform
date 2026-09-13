"""Read-only design audit for a future UIP-native Metals regime-probability authority."""
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
    parser.add_argument("--model-component-manifest", type=Path, required=True)
    parser.add_argument("--risk-manifest", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    native_cycle = read_json(args.native_cycle)
    model_component = read_json(args.model_component_manifest)
    risk = read_json(args.risk_manifest)
    methodology = read_json(args.methodology)

    restored = ((lineage.get("record_types") or {}).get("metals_regime_probability") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(v) for v in restored.get("payload_keys", []))

    models = methodology.get("models") or []
    model = models[0] if models and isinstance(models[0], dict) else {}
    registry_version = str(methodology.get("registry_version", ""))
    model_id = str(model.get("model_id", ""))

    forecasts = native_cycle.get("forecasts") or []
    by_asset: dict[str, list[dict]] = defaultdict(list)
    horizons: set[int] = set()
    model_ids: set[str] = set()
    methodology_versions: set[str] = set()
    confidence_values: list[float] = []
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
        "restored_regime_probability_family_present": restored_count > 0,
        "restored_regime_probability_schema_observed": len(restored_keys) > 0,
        "native_cycle_pass": native_cycle.get("status") == EXPECTED_NATIVE_CYCLE_STATUS,
        "native_cycle_has_forecasts": len(forecasts) > 0,
        "native_cycle_has_multiple_assets": len(by_asset) > 1,
        "native_cycle_has_multiple_horizons": len(horizons) > 1,
        "native_cycle_model_id_matches_registry": model_ids == {model_id} == {EXPECTED_MODEL_ID},
        "native_cycle_methodology_version_matches_registry": methodology_versions == {registry_version},
        "native_cycle_confidence_present": len(confidence_values) == len(forecasts),
        "model_component_authority_pass": model_component.get("status") == "METALS_NATIVE_MODEL_COMPONENT_V1_PASS",
        "model_component_authority_nonlegacy": model_component.get("legacy_equivalent") is False,
        "model_component_asset_count_matches_native_cycle": int(model_component.get("asset_count", -1)) == len(by_asset),
        "risk_authority_pass": risk.get("status") == "METALS_NATIVE_RISK_V1_PASS",
        "risk_authority_nonlegacy": risk.get("legacy_equivalent") is False,
        "benchmark_history_has_multiple_dates": int(benchmark_date_count) > 1,
        "benchmark_history_has_multiple_series": int(benchmark_series_count) > 1,
        "vehicle_history_has_multiple_dates": int(vehicle_date_count) > 1,
        "vehicle_history_has_multiple_series": int(vehicle_series_count) > 1,
    }

    design_ready = all(checks.values())
    decision = (
        "AUTHORIZE_UIP_NATIVE_METALS_REGIME_PROBABILITY_V1_DESIGN"
        if design_ready
        else "DO_NOT_AUTHORIZE_REGIME_PROBABILITY_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED"
    )

    evidence = {
        "status": "METALS_REGIME_PROBABILITY_AUTHORITY_DESIGN_AUDIT_PASS" if design_ready else "METALS_REGIME_PROBABILITY_AUTHORITY_DESIGN_AUDIT_FAIL_CLOSED",
        "decision": decision,
        "query_policy": "READ_ONLY_SELECT_ONLY",
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_regime_probability": {
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
        },
        "supporting_native_authorities": {
            "model_component": {
                "status": model_component.get("status"),
                "authority_id": model_component.get("authority_id"),
                "asset_count": model_component.get("asset_count"),
                "row_count": model_component.get("row_count"),
            },
            "risk": {
                "status": risk.get("status"),
                "authority_id": risk.get("authority_id"),
                "scope": risk.get("scope"),
                "vehicle_count": risk.get("vehicle_count"),
                "row_count": risk.get("row_count"),
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
        "candidate_authority_boundary": "BENCHMARK_COMMODITY_ASSET_ONLY",
        "missing_semantics_to_govern_before_builder": [
            "canonical regime label taxonomy and exact label count",
            "probability output schema and one-row-per-asset-regime grain",
            "probability normalization rule and fail-closed tolerance for sum-to-one",
            "regime classifier inputs and their versioned transformations",
            "relationship between forecast horizon and regime probability, including whether regimes are horizon-specific",
            "historical as-of evaluation cadence and temporal cutoff rule if retrospective probabilities are reconstructed",
            "same-day source revision policy for benchmark and vehicle observations",
            "calibration semantics: descriptive score normalization versus calibrated probability",
            "minimum evidence/completeness thresholds and unavailable-state behavior",
            "methodology-version transition policy",
            "explicit prohibition on copying restored legacy regime rows forward as fresh authority",
            "explicit prohibition on projecting vehicle-only risk authority into commodity probability without governed mapping",
        ],
        "notes": [
            "Design authorization does not authorize production regime-probability rows.",
            "The 12 restored regime-probability rows are evidence only; their row count does not define the new authority universe or taxonomy.",
            "Current UIP-native forecasts, model components, risk, and persisted observations provide candidate inputs, but no current certified regime-probability authority exists yet.",
            "Any V1 authority must remain legacy_equivalent=false and commodity-level unless a separate governed mapping is approved.",
            "Probability must not be claimed to be statistically calibrated unless calibration is explicitly implemented and certified.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print(f"METALS_REGIME_PROBABILITY_AUTHORITY_DESIGN={decision}")
    return 0 if design_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

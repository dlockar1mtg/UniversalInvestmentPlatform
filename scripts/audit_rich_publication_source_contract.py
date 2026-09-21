"""Read-only audit of whether latest source artifacts can reproduce the rich UIP presentation.

No database connection is opened and no publication is staged or activated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.crypto_current_price_projection import audit_crypto_current_price_v1


EXPECTED_MTG = {
    "premium": {
        "path": "docs/phase_9/uip_export/premium_research/mtg_secret_lair_premium_research.csv",
        "rows": 787,
        "sha256": "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333",
        "hash_mode": "canonical_crlf",
    },
    "collector": {
        "path": "docs/phase_9/uip_export/research_sidecars/mtg_collector_research.csv",
        "rows": 50,
        "sha256": "b81ee16a310f8a4f9dcbccf21047e31396df9810d53291cdb9b631fbe046d457",
        "hash_mode": "raw",
    },
    "collector_horizon": {
        "path": "docs/phase_9/uip_export/research_sidecars/mtg_collector_forecast_horizon.csv",
        "rows": 294,
        "sha256": "585257520197fff9700c0a9f1d1d517af60c1792d944f3f4dab1f65c564cf3e8",
        "hash_mode": "raw",
    },
    "precollector": {
        "path": "docs/phase_9/uip_export/research_sidecars/mtg_precollector_research.csv",
        "rows": 131,
        "sha256": "80d8a60ffcc35d688e6560ee94f2d1f910fb3cd961eea097d5ffd00862034f81",
        "hash_mode": "raw",
    },
    "precollector_scenario": {
        "path": "docs/phase_9/uip_export/research_sidecars/mtg_precollector_scenario_horizon.csv",
        "rows": 190,
        "sha256": "74caad4f8d39ce255455854ab5a5459779f6e73adc0afebc8269e769858aed0a",
        "hash_mode": "raw",
    },
}

REQUIRED_METALS_RICH_FAMILIES = {
    "price_history": "metals_price_history",
    "current_price": "metals_current_price",
    "data_freshness": "metals_data_freshness",
    "commodity_technical_context": "metals_commodity_technical_context",
    "model_component": "metals_model_component",
    "platform_health": "metals_platform_health",
    "recommendation_change": "metals_recommendation_change",
    "regime_probability": "metals_regime_probability",
    "uncertainty_adjusted": "metals_uncertainty_adjusted",
    "tactical_state": "tactical_state",
    "risk": "risk",
}

NATIVE_METALS_CERTIFIED_CONTRACTS = {
    "current_price": {
        "csv": "operations/metals/native_rich_history/metals_current_price.csv",
        "manifest": "operations/metals/native_rich_history/manifest.json",
        "manifest_status": "METALS_NATIVE_HISTORY_SIDECARS_PASS",
        "manifest_authority_key": "source_authority",
        "manifest_authority": "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
        "row_count_key": "current_price_row_count",
        "expected_rows": 11,
        "manifest_file_key": "metals_current_price.csv",
    },
    "price_history": {
        "csv": "operations/metals/native_rich_history/metals_price_history.csv",
        "manifest": "operations/metals/native_rich_history/manifest.json",
        "manifest_status": "METALS_NATIVE_HISTORY_SIDECARS_PASS",
        "manifest_authority_key": "source_authority",
        "manifest_authority": "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
        "row_count_key": "history_row_count",
        "minimum_rows": 1,
        "manifest_file_key": "metals_price_history.csv",
    },
    "data_freshness": {
        "csv": "operations/metals/native_freshness_v1/metals_data_freshness.csv",
        "manifest": "operations/metals/native_freshness_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_DATA_FRESHNESS_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_DATA_FRESHNESS_V1",
        "row_count_key": "row_count",
        "expected_rows": 20,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
    },
    "commodity_technical_context": {
        "csv": "operations/metals/native_commodity_technical_context_v1/metals_commodity_technical_context.csv",
        "manifest": "operations/metals/native_commodity_technical_context_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_COMMODITY_TECHNICAL_CONTEXT_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1",
        "row_count_key": "row_count",
        "expected_rows": 8,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "scope": "BENCHMARK_COMMODITY_MONTHLY_TECHNICAL_CONTEXT",
            "source_state_mode": "CURRENT_CERTIFIED_WORLD_BANK_MONTHLY_HISTORY_ONLY",
            "presentation_semantics": "DESCRIPTIVE_COMMODITY_TECHNICAL_CONTEXT_NOT_RECOMMENDATION_NOT_EXECUTION",
            "supported_asset_count": 8,
            "source_history_row_count": 6400,
            "ma50_supported": False,
            "ma200_supported": False,
            "unsupported_assets": {
                "metals:commodity:uranium": "CERTIFIED_EIA_SOURCE_IS_ANNUAL_AND_CANNOT_SUPPORT_MONTHLY_TECHNICAL_CONTEXT_V1"
            },
            "source_collection_performed": True,
        },
    },
    "platform_health": {
        "csv": "operations/metals/native_platform_health_v1/metals_platform_health.csv",
        "manifest": "operations/metals/native_platform_health_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_PLATFORM_HEALTH_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_PLATFORM_HEALTH_V1",
        "row_count_key": "row_count",
        "expected_rows": 1,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
    },
    "model_component": {
        "csv": "operations/metals/native_model_component_v1/metals_model_component.csv",
        "manifest": "operations/metals/native_model_component_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_MODEL_COMPONENT_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_MODEL_COMPONENT_V1",
        "row_count_key": "row_count",
        "expected_rows": 81,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_component_names": [
            "uip_native_benchmark_momentum",
            "uip_native_vehicle_confirmation",
            "uip_native_data_completeness_adjustment",
        ],
        "expected_source_model_ids": ["uip-metals-native-trend-v1"],
    },
    "risk": {
        "csv": "operations/metals/native_risk_v1/risk.csv",
        "manifest": "operations/metals/native_risk_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_RISK_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_RISK_V1",
        "row_count_key": "row_count",
        "expected_rows": 11,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.2",
            "scope": "VEHICLE_ONLY",
            "vehicle_count": 11,
            "lookback_observations": 252,
            "minimum_observations": 252,
            "return_convention": "SIMPLE_CLOSE_TO_CLOSE_DAILY_RETURN",
            "annualization_factor": 252,
            "var_method": "HISTORICAL_EMPIRICAL",
            "var_confidence_level": 0.95,
            "price_semantics": "UNADJUSTED_CLOSE",
            "source_authority": "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
            "same_date_multi_source_method": "LATEST_COLLECTED_REVISION_WINS",
            "conflicting_latest_timestamp_tie_behavior": "FAIL_CLOSED",
            "missing_or_invalid_collected_at_behavior": "FAIL_CLOSED",
        },
    },
    "recommendation_change": {
        "csv": "operations/metals/native_recommendation_change_v1/metals_recommendation_change.csv",
        "manifest": "operations/metals/native_recommendation_change_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1",
        "row_count_key": "change_row_count",
        "minimum_rows": 1,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "scope": "BENCHMARK_COMMODITY_ASSET_ONLY",
            "reconstruction_mode": "RETROSPECTIVE_CANONICAL_OBSERVATION_REPLAY",
            "model_id": "uip-metals-native-trend-v1",
            "source_methodology_version": "1.0.0",
            "evaluation_cadence": "UNION_OF_CANONICAL_BENCHMARK_AND_VEHICLE_OBSERVATION_DATES",
            "temporal_cutoff_rule": "OBSERVATION_DATE_LE_EVALUATION_DATE",
            "latest_state_asset_count": 9,
            "latest_state_parity": True,
            "first_observation_behavior": "BASELINE_ONLY_NO_CHANGE_EVENT",
            "no_op_behavior": "OMIT_REPEATED_RECOMMENDATION",
            "change_event_grain": "ONE_ROW_PER_COMMODITY_RECOMMENDATION_TRANSITION",
            "same_date_multi_source_method": "LATEST_COLLECTED_REVISION_WINS",
            "source_collection_performed": False,
            "vehicle_recommendation_projection_performed": False,
            "legacy_rows_copied_forward": False,
        },
    },
    "regime_probability": {
        "csv": "operations/metals/native_regime_probability_v1/metals_regime_probability.csv",
        "manifest": "operations/metals/native_regime_probability_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1",
        "row_count_key": "row_count",
        "expected_rows": 27,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "scope": "BENCHMARK_COMMODITY_ASSET_ONLY",
            "source_state_mode": "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY",
            "model_id": "uip-metals-native-trend-v1",
            "source_methodology_version": "1.0.0",
            "probability_grain": "ONE_ROW_PER_COMMODITY_PER_REGIME",
            "probability_interpretation": "DESCRIPTIVE_NORMALIZED_REGIME_SUPPORT_NOT_STATISTICALLY_CALIBRATED",
            "horizon_semantics": "HORIZON_INVARIANT_CURRENT_REGIME_REQUIRE_IDENTICAL_SOURCE_COMPONENTS_ACROSS_HORIZONS",
            "normalization_method": "PIECEWISE_DIRECTIONAL_SUPPORT_WITH_NEUTRAL_REMAINDER",
            "confidence_policy": "MULTIPLY_DIRECTIONAL_SUPPORT_BY_NATIVE_CONFIDENCE_AND_ASSIGN_REMAINDER_TO_NEUTRAL",
            "regime_taxonomy": ["POSITIVE_TREND", "NEUTRAL_OR_MIXED", "NEGATIVE_TREND"],
            "regime_count": 3,
            "asset_count": 9,
            "source_forecast_count": 27,
            "source_horizons_months": [12, 36, 60],
            "statistical_calibration_claimed": False,
            "source_collection_performed": False,
            "vehicle_risk_projection_performed": False,
            "commodity_to_vehicle_regime_projection_performed": False,
            "legacy_rows_copied_forward": False,
        },
    },
    "uncertainty_adjusted": {
        "csv": "operations/metals/native_uncertainty_adjusted_v1/metals_uncertainty_adjusted.csv",
        "manifest": "operations/metals/native_uncertainty_adjusted_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1",
        "row_count_key": "row_count",
        "expected_rows": 27,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "scope": "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON",
            "source_state_mode": "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY",
            "model_id": "uip-metals-native-trend-v1",
            "source_methodology_version": "1.0.0",
            "output_grain": "ONE_ROW_PER_COMMODITY_PER_FORECAST_HORIZON",
            "adjusted_quantity": "ONE_SIDED_CONFIDENCE_HAIRCUT_EXPECTED_RETURN",
            "formula": "adjusted_expected_return = raw_expected_return - abs(raw_expected_return) * (1 - confidence)",
            "uncertainty_penalty_formula": "abs(raw_expected_return) * (1 - confidence)",
            "adjustment_interpretation": "DESCRIPTIVE_CONSERVATIVE_CONFIDENCE_HAIRCUT_NOT_STATISTICALLY_CALIBRATED_INTERVAL",
            "confidence_semantics": "USE_NATIVE_FORECAST_CONFIDENCE_AS_GOVERNED_0_TO_1_SHRINKAGE_INPUT_ONLY",
            "horizon_semantics": "APPLY_IDENTICAL_FORMULA_INDEPENDENTLY_TO_EACH_NATIVE_FORECAST_HORIZON",
            "regime_probability_authority_id": "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1",
            "regime_probability_methodology_version": "1.0.0",
            "regime_semantics": "CERTIFIED_REGIME_PROBABILITY_V1_CONTEXT_ONLY_NO_NUMERIC_ADJUSTMENT",
            "risk_semantics": "VEHICLE_ONLY_RISK_V1_EXCLUDED_UNTIL_EXPLICIT_COMMODITY_MAPPING_IS_GOVERNED",
            "asset_count": 9,
            "source_forecast_count": 27,
            "source_horizons_months": [12, 36, 60],
            "statistical_calibration_claimed": False,
            "source_collection_performed": False,
            "vehicle_risk_projection_performed": False,
            "regime_numeric_adjustment_performed": False,
            "commodity_to_vehicle_adjusted_projection_performed": False,
            "legacy_rows_copied_forward": False,
            "cross_asset_ranking_performed": False,
            "portfolio_allocation_performed": False,
            "automatic_execution_performed": False,
        },
    },
    "tactical_state": {
        "csv": "operations/metals/native_tactical_state_v1/metals_tactical_state.csv",
        "manifest": "operations/metals/native_tactical_state_v1/manifest.json",
        "manifest_status": "METALS_NATIVE_TACTICAL_STATE_V1_PASS",
        "manifest_authority_key": "authority_id",
        "manifest_authority": "UIP_NATIVE_METALS_TACTICAL_STATE_V1",
        "row_count_key": "row_count",
        "expected_rows": 9,
        "require_nonlegacy": True,
        "output_sha_key": "output_sha256",
        "expected_manifest_values": {
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "scope": "BENCHMARK_COMMODITY_ASSET_ONLY",
            "source_state_mode": "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY",
            "model_id": "uip-metals-native-trend-v1",
            "source_methodology_version": "1.0.0",
            "output_grain": "ONE_ROW_PER_COMMODITY",
            "tactical_horizon_months": 12,
            "state_interpretation": "DESCRIPTIVE_12_MONTH_TACTICAL_ALIGNMENT_NOT_TRADE_INSTRUCTION",
            "taxonomy": [
                "TACTICAL_SUPPORTIVE",
                "TACTICAL_POSITIVE_BUT_MIXED",
                "TACTICAL_NEUTRAL",
                "TACTICAL_CAUTION",
                "TACTICAL_DEFENSIVE",
                "TACTICAL_CONFLICT",
            ],
            "asset_count": 9,
            "recommendation_semantics": "CURRENT_CERTIFIED_NATIVE_RECOMMENDATION_AS_STRATEGIC_DIRECTIONAL_CONTEXT",
            "regime_probability_authority_id": "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1",
            "regime_probability_methodology_version": "1.0.0",
            "regime_semantics": "CERTIFIED_REGIME_PROBABILITY_V1_DOMINANT_REGIME_AS_DESCRIPTIVE_CONTEXT",
            "uncertainty_adjusted_authority_id": "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1",
            "uncertainty_adjusted_methodology_version": "1.0.0",
            "uncertainty_semantics": "CERTIFIED_UNCERTAINTY_ADJUSTED_V1_12_MONTH_RETURN_AS_TACTICAL_DIRECTIONAL_CONTEXT",
            "risk_semantics": "VEHICLE_ONLY_RISK_V1_EXCLUDED_NO_COMMODITY_PROJECTION",
            "statistical_calibration_claimed": False,
            "source_collection_performed": False,
            "vehicle_risk_projection_performed": False,
            "vehicle_tactical_projection_performed": False,
            "legacy_rows_copied_forward": False,
            "legacy_action_mapping_reused": False,
            "legacy_classifier_reused": False,
            "missing_state_imputed": False,
            "cross_asset_ranking_performed": False,
            "portfolio_allocation_performed": False,
            "trade_sizing_performed": False,
            "automatic_execution_performed": False,
        },
    },
}

SAFETY_FALSE_KEYS = (
    "postgres_write_performed",
    "publication_staged",
    "publication_activated",
)


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_crlf_sha256(path: Path) -> str:
    raw = path.read_bytes()
    normalized_lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    canonical = normalized_lf.replace(b"\n", b"\r\n")
    return hashlib.sha256(canonical).hexdigest()


def inventory(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit_certified_metals_family(root: Path, family: str, spec: dict) -> dict:
    csv_path = root / str(spec["csv"])
    manifest_path = root / str(spec["manifest"])
    csv_exists = csv_path.is_file()
    manifest_exists = manifest_path.is_file()
    result = {
        "family": family,
        "csv": str(spec["csv"]),
        "manifest": str(spec["manifest"]),
        "csv_exists": csv_exists,
        "manifest_exists": manifest_exists,
        "pass": False,
    }
    if not csv_exists or not manifest_exists:
        return result

    manifest = load_json(manifest_path)
    rows = csv_rows(csv_path)
    actual_sha = sha256(csv_path)
    checks: dict[str, bool] = {
        "manifest_status": manifest.get("status") == spec["manifest_status"],
        "manifest_authority": manifest.get(spec["manifest_authority_key"]) == spec["manifest_authority"],
        "csv_row_count_matches_manifest": rows == int(manifest.get(spec["row_count_key"], -1)),
        "safety_flags_false": all(manifest.get(key) is False for key in SAFETY_FALSE_KEYS),
    }

    if "expected_rows" in spec:
        checks["expected_row_count"] = rows == int(spec["expected_rows"])
    if "minimum_rows" in spec:
        checks["minimum_row_count"] = rows >= int(spec["minimum_rows"])
    if spec.get("require_nonlegacy"):
        checks["legacy_equivalent_false"] = manifest.get("legacy_equivalent") is False
    if spec.get("output_sha_key"):
        checks["output_sha_matches_manifest"] = actual_sha == manifest.get(spec["output_sha_key"])
    if spec.get("manifest_file_key"):
        file_entry = (manifest.get("files") or {}).get(spec["manifest_file_key"], {})
        checks["manifest_file_row_count"] = rows == int(file_entry.get("row_count", -1))
        checks["manifest_file_sha"] = actual_sha == file_entry.get("sha256")
    if spec.get("expected_component_names"):
        checks["component_names"] = manifest.get("component_names") == spec["expected_component_names"]
    if spec.get("expected_source_model_ids"):
        checks["source_model_ids"] = manifest.get("source_model_ids") == spec["expected_source_model_ids"]
    for key, expected in (spec.get("expected_manifest_values") or {}).items():
        checks[f"manifest_{key}"] = manifest.get(key) == expected

    result.update(
        {
            "rows": rows,
            "sha256": actual_sha,
            "manifest_status": manifest.get("status"),
            "manifest_authority": manifest.get(spec["manifest_authority_key"]),
            "checks": checks,
            "pass": all(checks.values()),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crypto-artifact", type=Path)
    parser.add_argument("--metals-artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

    crypto_root = args.crypto_artifact.resolve() if args.crypto_artifact else None
    metals_root = args.metals_artifact.resolve()
    mtg_root = args.mtg_repo.resolve()
    if crypto_root is not None and not crypto_root.is_dir():
        raise RuntimeError(f"Crypto artifact root missing: {crypto_root}")
    if not metals_root.is_dir():
        raise RuntimeError(f"Metals artifact root missing: {metals_root}")
    if not mtg_root.is_dir():
        raise RuntimeError(f"MTG checkout missing: {mtg_root}")

    mtg = {}
    mtg_pass = True
    for key, spec in EXPECTED_MTG.items():
        relative = str(spec["path"])
        expected_rows = int(spec["rows"])
        expected_sha = str(spec["sha256"])
        hash_mode = str(spec["hash_mode"])
        path = mtg_root / relative
        exists = path.is_file()
        rows = csv_rows(path) if exists else None
        raw_sha = sha256(path) if exists else None
        certification_sha = canonical_crlf_sha256(path) if exists and hash_mode == "canonical_crlf" else raw_sha
        row_count_pass = exists and rows == expected_rows
        sha256_pass = exists and certification_sha == expected_sha
        passed = bool(row_count_pass and sha256_pass)
        mtg_pass = mtg_pass and passed
        mtg[key] = {
            "path": relative,
            "exists": exists,
            "rows": rows,
            "expected_rows": expected_rows,
            "row_count_pass": row_count_pass,
            "raw_sha256": raw_sha,
            "certification_sha256": certification_sha,
            "expected_sha256": expected_sha,
            "hash_mode": hash_mode,
            "sha256_pass": sha256_pass,
            "pass": passed,
        }

    files = inventory(metals_root)
    metals_families = {}
    certified_count = 0
    for key, needle in REQUIRED_METALS_RICH_FAMILIES.items():
        if key in NATIVE_METALS_CERTIFIED_CONTRACTS:
            contract_result = audit_certified_metals_family(
                metals_root, key, NATIVE_METALS_CERTIFIED_CONTRACTS[key]
            )
            passed = bool(contract_result["pass"])
            matches = [name for name in files if needle in name.lower()]
            contract_result["needle"] = needle
            contract_result["matches"] = matches
            metals_families[key] = contract_result
        else:
            matches = [name for name in files if needle in name.lower()]
            passed = False
            metals_families[key] = {
                "needle": needle,
                "matches": matches,
                "contract_defined": False,
                "pass": False,
            }
        if passed:
            certified_count += 1

    metals_pass = certified_count == len(REQUIRED_METALS_RICH_FAMILIES)
    crypto_current_price = (
        audit_crypto_current_price_v1(crypto_root)
        if crypto_root is not None
        else None
    )
    crypto_pass = True if crypto_current_price is None else bool(crypto_current_price["pass"])
    evidence = {
        "status": "PASS" if mtg_pass and metals_pass and crypto_pass else "FAIL_CLOSED",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "crypto_current_price_source_contract_pass": (
            None if crypto_current_price is None else bool(crypto_current_price["pass"])
        ),
        "crypto_current_price": crypto_current_price,
        "mtg_rich_source_contract_pass": mtg_pass,
        "mtg": mtg,
        "metals_rich_source_contract_pass": metals_pass,
        "metals_certified_family_count": certified_count,
        "metals_required_family_count": len(REQUIRED_METALS_RICH_FAMILIES),
        "metals_remaining_family_count": len(REQUIRED_METALS_RICH_FAMILIES) - certified_count,
        "metals_required_families": metals_families,
        "metals_artifact_file_count": len(files),
        "metals_artifact_files": files,
        "failure_policy": "NO_PRODUCTION_PUBLICATION_UNTIL_RICH_SOURCE_CONTRACTS_ARE_REPRODUCIBLE",
    }

    output = args.evidence_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ROOT = ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "crypto_persisted_recapture"
R2_EVIDENCE = ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal" / "crypto_r2_rehearsal_evidence.json"
CONTRACT = ROOT / "config" / "orchestration" / "r3_domain_review_contract.json"
OUTPUT = ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "crypto_r3_domain_review.json"

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"
ALLOWED_NATIVE_TO_UNIVERSAL = {
    "BUY": "buy",
    "ACCUMULATE": "accumulate",
    "HOLD": "hold",
    "WAIT": "watch",
    "REDUCE": "reduce",
    "SELL": "sell",
    "AVOID": "sell",
}
REQUIRED_DIMENSIONS = {
    "freshness_and_completeness",
    "native_self_consistency",
    "distribution_and_outliers",
    "change_from_prior_plausibility",
    "uip_semantic_preservation",
    "decision_readiness",
    "investigation_routing",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Missing required JSON authority: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise RuntimeError(f"Missing required dataset: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def nonempty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def parse_float(value: str, *, field: str, asset: str) -> float | None:
    if not nonempty(value):
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise RuntimeError(f"Non-numeric {field} for {asset}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise RuntimeError(f"Non-finite {field} for {asset}: {value!r}")
    return parsed


def numeric_summary(rows: list[dict[str, str]], fields: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in fields:
        values: list[float] = []
        missing = 0
        for row in rows:
            asset = row.get("universal_asset_id", "<unknown>")
            value = parse_float(row.get(field, ""), field=field, asset=asset)
            if value is None:
                missing += 1
            else:
                values.append(value)
        result[field] = {
            "count": len(values),
            "missing": missing,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": (sum(values) / len(values)) if values else None,
        }
    return result


def require(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise RuntimeError(message)
    checks.append(message)


def main() -> int:
    contract = load_json(CONTRACT)
    r2 = load_json(R2_EVIDENCE)

    if contract.get("milestone") != "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW":
        raise RuntimeError("Unexpected R3 milestone.")
    if set(contract.get("required_dimensions", [])) != REQUIRED_DIMENSIONS:
        raise RuntimeError("R3 required dimensions differ from governed contract.")
    crypto_contract = contract.get("domains", {}).get("crypto", {})
    if crypto_contract.get("review_authority_mode") != "R3_PERSISTED_RECAPTURE_REQUIRED":
        raise RuntimeError("Crypto R3 authority mode is not governed persisted recapture.")

    captures = sorted(path for path in CAPTURE_ROOT.iterdir() if path.is_dir()) if CAPTURE_ROOT.is_dir() else []
    if len(captures) != 1:
        raise RuntimeError(f"Expected exactly one governed Crypto R3 capture, found {len(captures)}")
    capture = captures[0]
    manifest = load_json(capture / "r3_crypto_capture_manifest.json")
    package_summary = load_json(capture / "package_summary.json")
    run_summary = load_json(capture / "run_summary.json")
    validation_report = load_json(capture / "validation_report.json")

    if manifest.get("status") != "UIP_R3_CRYPTO_PERSISTED_RECAPTURE_PASS":
        raise RuntimeError("Crypto R3 capture manifest is not PASS.")
    if manifest.get("authority_mode") != "R3_PERSISTED_RECAPTURE":
        raise RuntimeError("Crypto capture authority label is incorrect.")
    if manifest.get("is_exact_r2_output") is not False:
        raise RuntimeError("Crypto recapture is incorrectly labeled as exact R2 output.")
    if manifest.get("source_commit_or_version") != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("Crypto recapture source commit does not match certified native authority.")
    if manifest.get("source_database_unchanged") is not True:
        raise RuntimeError("Crypto source database unchanged evidence is not true.")
    if manifest.get("full_refresh") is not False:
        raise RuntimeError("Crypto R3 capture did not use governed incremental refresh.")

    datasets: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    for name in ("asset_master", "forecasts", "platform_status", "portfolio_positions", "recommendations", "risk_metrics"):
        datasets[name] = read_csv(capture / f"{name}.csv")

    rows = {name: data[1] for name, data in datasets.items()}
    observed_counts = {name: len(value) for name, value in rows.items()}
    manifest_counts = {key: int(value) for key, value in manifest.get("dataset_counts", {}).items()}
    if observed_counts != manifest_counts:
        raise RuntimeError(f"Observed dataset counts do not match capture manifest: {observed_counts} != {manifest_counts}")
    if package_summary.get("dataset_counts") != manifest.get("dataset_counts"):
        raise RuntimeError("Package summary counts do not reconcile to capture manifest.")
    if run_summary.get("universal_export", {}).get("dataset_counts") != manifest.get("dataset_counts"):
        raise RuntimeError("Run summary export counts do not reconcile to capture manifest.")

    checks: list[str] = []
    anomalies: list[dict[str, Any]] = []
    governed_gaps = [str(manifest.get("governed_gap", "")).strip()]
    governed_gaps = [gap for gap in governed_gaps if gap]

    asset_rows = rows["asset_master"]
    asset_ids = [row.get("universal_asset_id", "").strip() for row in asset_rows]
    require(all(asset_ids), "All Crypto asset-master rows have universal_asset_id", checks)
    require(len(asset_ids) == len(set(asset_ids)), "Crypto asset-master universal_asset_id values are unique", checks)
    asset_set = set(asset_ids)

    for dataset_name in ("forecasts", "recommendations", "risk_metrics"):
        ids = [row.get("universal_asset_id", "").strip() for row in rows[dataset_name]]
        require(all(ids), f"All {dataset_name} rows have universal_asset_id", checks)
        require(set(ids).issubset(asset_set), f"All {dataset_name} asset IDs resolve to current asset master", checks)

    recommendation_rows = rows["recommendations"]
    rec_by_asset = Counter(row.get("universal_asset_id", "").strip() for row in recommendation_rows)
    require(all(count == 1 for count in rec_by_asset.values()), "Current Crypto recommendation rows are unique per represented asset", checks)
    require(set(rec_by_asset) == asset_set, "Current Crypto recommendations cover the current source-defined asset universe", checks)

    mapping_evidence: list[dict[str, str]] = []
    for row in recommendation_rows:
        asset = row.get("universal_asset_id", "").strip()
        native = row.get("platform_native_label", "").strip().upper()
        universal = row.get("recommendation", "").strip().lower()
        if native not in ALLOWED_NATIVE_TO_UNIVERSAL:
            raise RuntimeError(f"Unknown Crypto native recommendation label fails closed: {asset}={native!r}")
        expected = ALLOWED_NATIVE_TO_UNIVERSAL[native]
        if universal != expected:
            raise RuntimeError(f"Crypto recommendation mapping mismatch for {asset}: native={native}, universal={universal}, expected={expected}")
        mapping_evidence.append({"asset": asset, "native": native, "universal": universal})
    checks.append("Certified Crypto native recommendation vocabulary and deterministic universal normalization are preserved")

    risk_rows = rows["risk_metrics"]
    risk_by_asset = Counter(row.get("universal_asset_id", "").strip() for row in risk_rows)
    require(all(count == 1 for count in risk_by_asset.values()), "Current Crypto risk rows are unique per represented asset", checks)
    require(set(risk_by_asset) == asset_set, "Current Crypto risk metrics cover the current source-defined asset universe", checks)

    position_rows = rows["portfolio_positions"]
    require(len(position_rows) == 0, "Absent Crypto holdings remain absent; no positions were synthesized", checks)

    status_rows = rows["platform_status"]
    require(len(status_rows) == 1, "Crypto platform status contains exactly one row for the recapture run", checks)
    status_row = status_rows[0]
    require(status_row.get("run_status", "").strip().lower() == "success", "Crypto platform_status run_status is native success", checks)
    require(status_row.get("run_id", "").strip() == manifest.get("run_id"), "Crypto platform_status run_id matches capture manifest", checks)
    require(nonempty(status_row.get("data_as_of_date")), "Crypto platform_status data_as_of_date is populated", checks)
    error_count = parse_float(status_row.get("error_count", ""), field="error_count", asset="platform_status")
    require(error_count == 0, "Crypto platform_status reports zero producer errors", checks)

    forecast_rows = rows["forecasts"]
    for row in forecast_rows:
        asset = row.get("universal_asset_id", "").strip()
        horizon = parse_float(row.get("forecast_horizon_months", ""), field="forecast_horizon_months", asset=asset)
        if horizon is None or horizon <= 0:
            raise RuntimeError(f"Crypto forecast horizon must be positive for {asset}")
        probability = parse_float(row.get("probability_positive_return", ""), field="probability_positive_return", asset=asset)
        if probability is not None and not (0.0 <= probability <= 1.0):
            raise RuntimeError(f"Crypto probability_positive_return outside mathematical probability bounds for {asset}: {probability}")
        confidence = parse_float(row.get("forecast_confidence", ""), field="forecast_confidence", asset=asset)
        if confidence is not None and not (0.0 <= confidence <= 100.0):
            raise RuntimeError(f"Crypto forecast_confidence outside certified 0-to-100 score bounds for {asset}: {confidence}")
        for field in ("current_value", "forecast_value_base", "forecast_value_bear", "forecast_value_bull", "expected_total_return", "expected_cagr"):
            parse_float(row.get(field, ""), field=field, asset=asset)
    checks.append("Crypto forecast numeric fields are finite; probability_positive_return remains within 0-to-1 bounds and forecast_confidence remains within certified 0-to-100 score bounds when populated")

    forecast_distribution = numeric_summary(
        forecast_rows,
        [
            "current_value",
            "forecast_value_base",
            "forecast_value_bear",
            "forecast_value_bull",
            "expected_total_return",
            "expected_cagr",
            "probability_positive_return",
            "forecast_confidence",
        ],
    )
    recommendation_distribution = numeric_summary(
        recommendation_rows,
        ["normalized_score", "confidence_score", "platform_native_score", "target_weight", "minimum_weight", "maximum_weight"],
    )
    risk_distribution = numeric_summary(
        risk_rows,
        [
            "risk_score",
            "annualized_volatility",
            "maximum_drawdown",
            "downside_deviation",
            "value_at_risk_95",
            "liquidity_risk_score",
            "concentration_risk_score",
            "model_risk_score",
            "data_quality_score",
        ],
    )

    native_label_counts = dict(sorted(Counter(row.get("platform_native_label", "").strip().upper() for row in recommendation_rows).items()))
    universal_action_counts = dict(sorted(Counter(row.get("recommendation", "").strip().lower() for row in recommendation_rows).items()))
    risk_level_counts = dict(sorted(Counter(row.get("risk_level", "").strip() for row in risk_rows).items()))
    horizon_counts = dict(sorted(Counter(row.get("forecast_horizon_months", "").strip() for row in forecast_rows).items()))
    forecast_method_counts = dict(sorted(Counter(row.get("forecast_method", "").strip() for row in forecast_rows).items()))
    scenario_counts = dict(sorted(Counter(row.get("scenario_name", "").strip() for row in forecast_rows).items()))

    r2_history_counts = r2.get("history_counts", {})
    recapture_counts = manifest.get("dataset_counts", {})
    count_comparison = {
        key: {
            "r2": int(r2_history_counts.get(key, -1)),
            "recapture": int(recapture_counts.get(key, -1)),
            "same": int(r2_history_counts.get(key, -1)) == int(recapture_counts.get(key, -1)),
        }
        for key in recapture_counts
    }
    if not all(item["same"] for item in count_comparison.values()):
        anomalies.append({"type": "population_count_change_from_r2", "details": count_comparison})

    validation_status = str(validation_report.get("status", "")).upper()
    if validation_status not in {"PASS", "VALID"}:
        raise RuntimeError(f"Crypto native validation report is not PASS/VALID: {validation_report.get('status')!r}")
    checks.append("Crypto native universal-export validation report is PASS")

    dimension_results = {
        "freshness_and_completeness": {
            "status": "PASS",
            "evidence": {
                "run_id": manifest.get("run_id"),
                "data_as_of_date": status_row.get("data_as_of_date"),
                "producer_error_count": int(error_count or 0),
                "dataset_counts": observed_counts,
                "native_validation_status": validation_report.get("status"),
            },
        },
        "native_self_consistency": {
            "status": "PASS",
            "evidence": {
                "asset_ids_unique": True,
                "recommendations_cover_current_universe": True,
                "risk_metrics_cover_current_universe": True,
                "native_to_universal_mapping": mapping_evidence,
                "positions_synthesized": False,
            },
        },
        "distribution_and_outliers": {
            "status": "PASS",
            "evidence": {
                "forecast_numeric_summary": forecast_distribution,
                "recommendation_numeric_summary": recommendation_distribution,
                "risk_numeric_summary": risk_distribution,
                "native_recommendation_label_counts": native_label_counts,
                "universal_action_counts": universal_action_counts,
                "risk_level_counts": risk_level_counts,
                "forecast_horizon_counts": horizon_counts,
                "forecast_method_counts": forecast_method_counts,
                "scenario_counts": scenario_counts,
                "note": "R3 records distributions and mathematical invalidities without inventing universal investment thresholds or treating native extremes as defects solely because they are extreme.",
            },
        },
        "change_from_prior_plausibility": {
            "status": "PASS_WITH_GOVERNED_GAP",
            "evidence": {
                "r2_prior_run_id": manifest.get("r2_prior_run_id"),
                "recapture_run_id": manifest.get("run_id"),
                "population_count_comparison": count_comparison,
                "exact_row_to_row_r2_comparison_available": False,
                "note": "Exact row-level R2 Crypto package was not retained; only governed prior-cycle summary evidence may be compared.",
            },
        },
        "uip_semantic_preservation": {
            "status": "PASS",
            "evidence": {
                "source_commit_or_version": manifest.get("source_commit_or_version"),
                "source_database_unchanged": manifest.get("source_database_unchanged"),
                "authority_mode": manifest.get("authority_mode"),
                "is_exact_r2_output": manifest.get("is_exact_r2_output"),
                "certified_native_recommendation_mapping_preserved": all(item["universal"] == ALLOWED_NATIVE_TO_UNIVERSAL[item["native"]] for item in mapping_evidence),
                "absent_holdings_preserved": len(position_rows) == 0,
                "native_risk_semantics_not_normalized": True,
            },
        },
        "decision_readiness": {
            "status": "PASS_WITH_GOVERNED_GAP",
            "evidence": {
                "bounded_use": "Crypto native intelligence may enter later UIP portfolio methodology with the exact-R2 row-comparison limitation disclosed. This review does not authorize cross-asset ranking, allocation weights, or trade execution.",
                "predictive_accuracy_certified": False,
            },
        },
        "investigation_routing": {
            "status": "PASS",
            "evidence": {
                "material_native_defect_detected": False,
                "uip_mapping_defect_detected": False,
                "investigation_owner": None,
                "routing_rule": "Any later confirmed Crypto source/model defect routes to dlockar1mtg/CryptoIntelligencePlatform; UIP mapping/import/lineage defects route to UIP.",
            },
        },
    }

    finding = "PASS_WITH_GOVERNED_GAPS"
    decision_readiness_scope = (
        "Decision-ready as bounded Crypto native evidence for later governed UIP portfolio methodology. "
        "R3 preserves the missing exact R2 row-to-row comparison as a governed gap and does not certify forecast predictive accuracy."
    )
    prohibited_downstream_uses = [
        "cross_asset_ranking_from_native_crypto_scores",
        "universal_risk_score_from_crypto_native_risk_fields",
        "portfolio_allocation_weights_from_native_recommendations",
        "automatic_trade_or_purchase_execution",
        "claim_of_exact_row_to_row_change_from_r2",
        "claim_of_predictive_accuracy_from_r3_plausibility_review",
    ]

    payload = {
        "domain_id": "crypto",
        "milestone": "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW",
        "r2_evidence_authority": str(R2_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
        "review_authority_mode": "R3_PERSISTED_RECAPTURE",
        "review_package": str(capture.relative_to(ROOT)).replace("\\", "/"),
        "source_commit_or_native_boundary": manifest.get("source_commit_or_version"),
        "data_as_of": status_row.get("data_as_of_date"),
        "dimension_results": dimension_results,
        "checks_performed": checks,
        "observed_anomalies": anomalies,
        "governed_gaps": governed_gaps,
        "finding": finding,
        "decision_readiness_scope": decision_readiness_scope,
        "prohibited_downstream_uses": prohibited_downstream_uses,
        "investigation_owner": None,
        "lineage_pointers": [
            str((capture / "r3_crypto_capture_manifest.json").relative_to(ROOT)).replace("\\", "/"),
            str((capture / "run_summary.json").relative_to(ROOT)).replace("\\", "/"),
            str((capture / "package_summary.json").relative_to(ROOT)).replace("\\", "/"),
            str((capture / "validation_report.json").relative_to(ROOT)).replace("\\", "/"),
            str(R2_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "docs/project_control/R3_GOVERNANCE_AND_DOMAIN_REVIEW_STANDARD.md",
            "config/orchestration/r3_domain_review_contract.json",
        ],
        "population_count_comparison": count_comparison,
        "cross_asset_ranking_created": False,
        "allocation_policy_created": False,
        "automatic_execution_created": False,
        "predictive_accuracy_certified": False,
        "next_gate": "R3_METALS_OUTPUT_RATIONALITY_REVIEW_AFTER_CRYPTO_EVIDENCE_COMMIT",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("UIP_R3_CRYPTO_OUTPUT_RATIONALITY_REVIEW=PASS_WITH_GOVERNED_GAPS")
    print(f"EVIDENCE_OUTPUT={OUTPUT}")
    print("DECISION_READY_BOUNDED=TRUE")
    print("PREDICTIVE_ACCURACY_CERTIFIED=FALSE")
    print("CROSS_ASSET_RANKING_CREATED=FALSE")
    print("ALLOCATION_POLICY_CREATED=FALSE")
    print("AUTOMATIC_EXECUTION_CREATED=FALSE")
    print("NEXT_GATE=R3_METALS_OUTPUT_RATIONALITY_REVIEW_AFTER_CRYPTO_EVIDENCE_COMMIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

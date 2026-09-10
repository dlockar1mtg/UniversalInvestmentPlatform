"""Build UIP-native Metals platform-health sidecar from certified native evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

AUTHORITY_ID = "UIP_NATIVE_METALS_PLATFORM_HEALTH_V1"
FRESHNESS_AUTHORITY = "UIP_NATIVE_METALS_DATA_FRESHNESS_V1"
HISTORY_STATUS = "METALS_NATIVE_HISTORY_SIDECARS_PASS"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values: list[float]) -> float:
    if not values:
        raise RuntimeError("cannot score an empty evidence set")
    return sum(values) / len(values)


def grade(score: float, thresholds: list[dict]) -> str:
    for item in sorted(thresholds, key=lambda row: float(row["minimum_score"]), reverse=True):
        if score >= float(item["minimum_score"]):
            return str(item["grade"])
    raise RuntimeError("grade thresholds do not cover score")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freshness", type=Path, required=True)
    parser.add_argument("--freshness-manifest", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--history-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path("config/presentation/metals_platform_health_v1.json"))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    if contract.get("authority_id") != AUTHORITY_ID:
        raise RuntimeError("unexpected platform-health authority_id")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("native platform health V1 must remain non-legacy-equivalent")

    freshness_rows = read_csv(args.freshness)
    freshness_manifest = read_json(args.freshness_manifest)
    native_cycle = read_json(args.native_cycle)
    history_manifest = read_json(args.history_manifest)

    if freshness_manifest.get("authority_id") != FRESHNESS_AUTHORITY:
        raise RuntimeError("freshness sidecar is not certified V1 authority")
    if freshness_manifest.get("status") != "METALS_NATIVE_DATA_FRESHNESS_V1_PASS":
        raise RuntimeError("freshness sidecar did not pass")
    if history_manifest.get("status") != HISTORY_STATUS:
        raise RuntimeError("native history sidecar did not pass")
    if native_cycle.get("status") != "PASS":
        raise RuntimeError("native cycle did not pass")

    expected_forecasts = int(contract["expected_native_forecast_count"])
    expected_assets = int(contract["expected_native_asset_count"])
    expected_freshness = int(contract["expected_freshness_subject_count"])
    expected_current = int(contract["expected_current_price_count"])

    forecasts = list(native_cycle.get("forecasts", []))
    if not forecasts:
        raise RuntimeError("native cycle contains no forecasts")

    asset_ids = {str(row.get("asset_id", "")).strip() for row in forecasts if str(row.get("asset_id", "")).strip()}
    freshness_score = round(mean([float(row["health_score"]) for row in freshness_rows]), 2)
    model_confidence_score = round(mean([float(row["confidence"]) * 100.0 for row in forecasts]), 2)

    valid_labels = {str(value).upper() for value in contract["recommendation_labels"]}
    valid_recommendations = sum(str(row.get("recommendation", "")).strip().upper() in valid_labels for row in forecasts)
    valid_row_coverage = valid_recommendations / len(forecasts)
    recommended_assets = {
        str(row.get("asset_id", "")).strip()
        for row in forecasts
        if str(row.get("recommendation", "")).strip().upper() in valid_labels
    }
    asset_coverage = len(recommended_assets) / expected_assets
    recommendation_quality_score = round(100.0 * min(valid_row_coverage, asset_coverage), 2)

    native_cycle_gate = len(forecasts) == expected_forecasts and len(asset_ids) == expected_assets
    freshness_gate = len(freshness_rows) == expected_freshness and int(freshness_manifest.get("row_count", -1)) == expected_freshness
    current_price_gate = int(history_manifest.get("current_price_row_count", -1)) == expected_current
    history_gate = int(history_manifest.get("history_row_count", 0)) > 0
    gates = [native_cycle_gate, freshness_gate, current_price_gate, history_gate]
    pipeline_completeness_score = round(100.0 * sum(gates) / len(gates), 2)

    weights = contract["component_weights"]
    if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise RuntimeError("platform-health component weights must sum to 1")
    components = {
        "data_freshness_score": freshness_score,
        "model_confidence_score": model_confidence_score,
        "recommendation_quality_score": recommendation_quality_score,
        "pipeline_completeness_score": pipeline_completeness_score,
    }
    overall = round(sum(components[key] * float(weights[key]) for key in components), 2)
    platform_grade = grade(overall, contract["grade_thresholds"])
    as_of = str(native_cycle.get("as_of_date") or max(str(row["as_of_date"]) for row in forecasts))
    decision_run_id = f"{AUTHORITY_ID}:{as_of}"
    explanation = (
        f"{AUTHORITY_ID} operational health: freshness {freshness_score:.2f}, model confidence "
        f"{model_confidence_score:.2f}, recommendation integrity {recommendation_quality_score:.2f}, "
        f"pipeline completeness {pipeline_completeness_score:.2f}; weighted overall {overall:.2f} ({platform_grade})."
    )

    row = {
        "decision_run_id": decision_run_id,
        "data_freshness_score": f"{freshness_score:.2f}",
        "model_confidence_score": f"{model_confidence_score:.2f}",
        "recommendation_quality_score": f"{recommendation_quality_score:.2f}",
        "pipeline_completeness_score": f"{pipeline_completeness_score:.2f}",
        "overall_platform_health": f"{overall:.2f}",
        "platform_grade": platform_grade,
        "explanation": explanation,
    }
    expected_fields = list(contract["required_output_fields"])
    if list(row.keys()) != expected_fields:
        raise RuntimeError("builder output fields do not match frozen V1 contract")

    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / "metals_platform_health.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=expected_fields)
        writer.writeheader()
        writer.writerow(row)

    manifest = {
        "status": "METALS_NATIVE_PLATFORM_HEALTH_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": contract["schema_version"],
        "legacy_equivalent": False,
        "row_count": 1,
        "as_of": as_of,
        "component_scores": components,
        "overall_platform_health": overall,
        "platform_grade": platform_grade,
        "evidence_gates": {
            "native_cycle_expected_shape": native_cycle_gate,
            "freshness_expected_shape": freshness_gate,
            "current_price_expected_shape": current_price_gate,
            "history_nonempty": history_gate,
        },
        "output_sha256": sha256(output),
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "source_collection_performed": False,
    }
    (args.output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_PLATFORM_HEALTH_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

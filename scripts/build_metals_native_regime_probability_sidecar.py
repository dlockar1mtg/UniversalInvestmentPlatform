"""Build UIP-native Metals Regime Probability V1 from the current certified native cycle."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: object, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite {name}: {value}")
    return number


def _component_dict(row: dict) -> dict:
    raw = row.get("component_json")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("native forecast is missing component_json")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("component_json must decode to an object")
    return parsed


def compute_probabilities(
    *,
    benchmark_momentum: float,
    vehicle_confirmation: float,
    confidence: float,
    positive_boundary: float,
    negative_boundary_abs: float,
    benchmark_weight: float,
    vehicle_weight: float,
    denominator: float,
) -> tuple[float, dict[str, float]]:
    if positive_boundary <= 0 or negative_boundary_abs <= 0 or denominator <= 0:
        raise RuntimeError("invalid regime-probability boundary configuration")
    if not 0.0 <= confidence <= 1.0:
        raise RuntimeError(f"confidence out of range: {confidence}")

    directional_signal = (
        benchmark_weight * benchmark_momentum + vehicle_weight * vehicle_confirmation
    ) / denominator

    if directional_signal >= 0:
        directional_support = min(1.0, directional_signal / positive_boundary)
        positive = directional_support * confidence
        negative = 0.0
    else:
        directional_support = min(1.0, abs(directional_signal) / negative_boundary_abs)
        positive = 0.0
        negative = directional_support * confidence

    neutral = 1.0 - positive - negative
    probabilities = {
        "POSITIVE_TREND": positive,
        "NEUTRAL_OR_MIXED": neutral,
        "NEGATIVE_TREND": negative,
    }
    return directional_signal, probabilities


def _stable_dominant(probabilities: dict[str, float], taxonomy: list[str]) -> tuple[str, float]:
    order = {label: index for index, label in enumerate(taxonomy)}
    label = max(taxonomy, key=lambda item: (probabilities[item], -order[item]))
    return label, probabilities[label]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    methodology = read_json(args.methodology)
    native_cycle = read_json(args.native_cycle)

    if contract.get("authority_id") != "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1":
        raise RuntimeError("unexpected regime-probability authority")
    if contract.get("scope") != "BENCHMARK_COMMODITY_ASSET_ONLY":
        raise RuntimeError("unexpected regime-probability scope")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("Regime Probability V1 must remain non-legacy-equivalent")
    if contract.get("source_state_mode") != "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY":
        raise RuntimeError("unsupported source-state mode")
    if native_cycle.get("status") != "PASS":
        raise RuntimeError("current native cycle is not PASS")

    models = methodology.get("models") or []
    if not models or not isinstance(models[0], dict):
        raise RuntimeError("methodology registry is missing model definition")
    model = models[0]
    model_id = str(model.get("model_id", ""))
    source_methodology_version = str(methodology.get("registry_version", ""))
    if model_id != contract.get("model_id"):
        raise RuntimeError("contract model_id does not match methodology registry")

    recommendation_policy = model.get("recommendation_policy") or {}
    positive_boundary = _finite(recommendation_policy.get("buy_min_return"), "buy_min_return")
    hold_boundary = _finite(recommendation_policy.get("hold_min_return"), "hold_min_return")
    if hold_boundary >= 0:
        raise RuntimeError("hold_min_return must be negative for V1 neutral boundary semantics")
    negative_boundary_abs = abs(hold_boundary)

    weights = contract.get("directional_component_weights") or {}
    benchmark_weight = _finite(weights.get("benchmark_momentum"), "benchmark_momentum weight")
    vehicle_weight = _finite(weights.get("vehicle_confirmation"), "vehicle_confirmation weight")
    denominator = _finite(contract.get("directional_signal_denominator"), "directional_signal_denominator")
    if not math.isclose(benchmark_weight + vehicle_weight, denominator, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("directional signal denominator must equal governed directional weights")

    taxonomy = list(contract.get("regime_taxonomy") or [])
    expected_taxonomy = ["POSITIVE_TREND", "NEUTRAL_OR_MIXED", "NEGATIVE_TREND"]
    if taxonomy != expected_taxonomy:
        raise RuntimeError(f"unexpected regime taxonomy: {taxonomy}")

    minimum = contract.get("minimum_evidence") or {}
    min_benchmark = int(minimum.get("benchmark_observation_count", 0))
    min_vehicle = int(minimum.get("vehicle_series_count", 0))
    if minimum.get("insufficient_evidence_behavior") != "FAIL_CLOSED":
        raise RuntimeError("Regime Probability V1 must fail closed on insufficient evidence")

    normalization = contract.get("normalization") or {}
    tolerance = _finite(normalization.get("sum_to_one_tolerance"), "sum_to_one_tolerance")
    lower = _finite(normalization.get("probability_minimum"), "probability_minimum")
    upper = _finite(normalization.get("probability_maximum"), "probability_maximum")

    grouped: dict[str, list[dict]] = defaultdict(list)
    forecasts = native_cycle.get("forecasts") or []
    for row in forecasts:
        asset_id = str(row.get("asset_id", "")).strip()
        if not asset_id:
            raise RuntimeError("native forecast missing asset_id")
        grouped[asset_id].append(row)
    if not grouped:
        raise RuntimeError("native cycle contains no assets")

    output_rows: list[dict[str, object]] = []
    dominant_counts: dict[str, int] = {label: 0 for label in taxonomy}
    as_of_dates: set[str] = set()
    source_horizons: set[int] = set()

    for asset_id, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: int(row.get("horizon_months", 0)))
        components = [_component_dict(row) for row in rows]
        component_signatures = {
            (
                round(_finite(item.get("benchmark_momentum"), "benchmark_momentum"), 12),
                round(_finite(item.get("vehicle_confirmation"), "vehicle_confirmation"), 12),
                int(item.get("benchmark_observation_count", 0)),
                int(item.get("vehicle_series_count", 0)),
            )
            for item in components
        }
        confidences = {round(_finite(row.get("confidence"), "confidence"), 12) for row in rows}
        model_ids = {str(row.get("model_id", "")) for row in rows}
        methodology_versions = {str(row.get("methodology_version", "")) for row in rows}
        as_of = {str(row.get("as_of_date", "")) for row in rows}
        if len(component_signatures) != 1 or len(confidences) != 1 or len(as_of) != 1:
            raise RuntimeError(f"source components/confidence/as-of vary across horizons for {asset_id}")
        if model_ids != {model_id}:
            raise RuntimeError(f"source model mismatch for {asset_id}: {model_ids}")
        if methodology_versions != {source_methodology_version}:
            raise RuntimeError(f"source methodology mismatch for {asset_id}: {methodology_versions}")

        benchmark_momentum, vehicle_confirmation, benchmark_count, vehicle_count = next(iter(component_signatures))
        confidence = next(iter(confidences))
        if benchmark_count < min_benchmark or vehicle_count < min_vehicle:
            raise RuntimeError(
                f"insufficient evidence for {asset_id}: benchmark_count={benchmark_count}, vehicle_count={vehicle_count}"
            )

        directional_signal, probabilities = compute_probabilities(
            benchmark_momentum=benchmark_momentum,
            vehicle_confirmation=vehicle_confirmation,
            confidence=confidence,
            positive_boundary=positive_boundary,
            negative_boundary_abs=negative_boundary_abs,
            benchmark_weight=benchmark_weight,
            vehicle_weight=vehicle_weight,
            denominator=denominator,
        )
        total = sum(probabilities.values())
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=tolerance):
            raise RuntimeError(f"regime probabilities do not sum to one for {asset_id}: {total}")
        if any(value < lower - tolerance or value > upper + tolerance for value in probabilities.values()):
            raise RuntimeError(f"regime probability outside governed bounds for {asset_id}: {probabilities}")

        dominant_regime, dominant_probability = _stable_dominant(probabilities, taxonomy)
        dominant_counts[dominant_regime] += 1
        as_of_date = next(iter(as_of))
        as_of_dates.add(as_of_date)
        source_horizons.update(int(row.get("horizon_months")) for row in rows)

        for regime in taxonomy:
            output_rows.append(
                {
                    "universal_asset_id": f"metals:commodity:{asset_id.lower()}",
                    "as_of_date": as_of_date,
                    "regime": regime,
                    "probability": round(probabilities[regime], 12),
                    "dominant_regime": dominant_regime,
                    "dominant_probability": round(dominant_probability, 12),
                    "directional_signal": round(directional_signal, 12),
                    "confidence": round(confidence, 12),
                    "model_id": model_id,
                    "source_methodology_version": source_methodology_version,
                    "authority_id": contract["authority_id"],
                    "methodology_version": contract["methodology_version"],
                    "probability_interpretation": contract["probability_interpretation"],
                }
            )

    expected_rows = len(grouped) * len(taxonomy)
    if len(output_rows) != expected_rows:
        raise RuntimeError("unexpected regime-probability output row count")

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "metals_regime_probability.csv"
    fields = list(contract["required_output_fields"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    manifest = {
        "status": "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS",
        "authority_id": contract["authority_id"],
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": contract["scope"],
        "source_state_mode": contract["source_state_mode"],
        "probability_interpretation": contract["probability_interpretation"],
        "probability_grain": contract["probability_grain"],
        "horizon_semantics": contract["horizon_semantics"],
        "regime_taxonomy": taxonomy,
        "regime_count": len(taxonomy),
        "asset_count": len(grouped),
        "row_count": len(output_rows),
        "source_forecast_count": len(forecasts),
        "source_horizons_months": sorted(source_horizons),
        "source_as_of_dates": sorted(as_of_dates),
        "model_id": model_id,
        "source_methodology_version": source_methodology_version,
        "normalization_method": normalization.get("method"),
        "sum_to_one_tolerance": tolerance,
        "neutral_positive_boundary": positive_boundary,
        "neutral_negative_boundary": -negative_boundary_abs,
        "confidence_policy": contract["confidence_policy"],
        "dominant_regime_asset_counts": dominant_counts,
        "contract_sha256": sha256_file(args.contract),
        "methodology_registry_sha256": sha256_file(args.methodology),
        "native_cycle_sha256": sha256_file(args.native_cycle),
        "output_sha256": sha256_file(csv_path),
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "vehicle_risk_projection_performed": False,
        "commodity_to_vehicle_regime_projection_performed": False,
        "legacy_rows_copied_forward": False,
        "statistical_calibration_claimed": False,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_REGIME_PROBABILITY_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

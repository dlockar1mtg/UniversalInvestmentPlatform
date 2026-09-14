"""Build UIP-native Metals Tactical State V1 from certified commodity authorities."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

POSITIVE_RECOMMENDATIONS = {"STRONG_BUY", "BUY"}
NEGATIVE_RECOMMENDATIONS = {"REDUCE", "AVOID"}
EXPECTED_RECOMMENDATIONS = POSITIVE_RECOMMENDATIONS | {"HOLD"} | NEGATIVE_RECOMMENDATIONS
EXPECTED_REGIMES = {"POSITIVE_TREND", "NEUTRAL_OR_MIXED", "NEGATIVE_TREND"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value: object, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite {name}: {value}")
    return number


def classify_tactical_state(recommendation: str, adjusted_return: float, regime: str) -> tuple[str, str]:
    if recommendation not in EXPECTED_RECOMMENDATIONS:
        raise RuntimeError(f"unsupported recommendation: {recommendation}")
    if regime not in EXPECTED_REGIMES:
        raise RuntimeError(f"unsupported regime: {regime}")

    if recommendation in POSITIVE_RECOMMENDATIONS:
        if adjusted_return > 0.0 and regime == "POSITIVE_TREND":
            return "TACTICAL_SUPPORTIVE", "POSITIVE_RECOMMENDATION_POSITIVE_12M_ADJUSTED_RETURN_POSITIVE_REGIME"
        if adjusted_return > 0.0:
            return "TACTICAL_POSITIVE_BUT_MIXED", "POSITIVE_RECOMMENDATION_POSITIVE_12M_ADJUSTED_RETURN_NONPOSITIVE_REGIME"
        return "TACTICAL_CAUTION", "POSITIVE_RECOMMENDATION_NONPOSITIVE_12M_ADJUSTED_RETURN"

    if recommendation == "HOLD":
        return "TACTICAL_NEUTRAL", "HOLD_RECOMMENDATION"

    if adjusted_return < 0.0 and regime == "NEGATIVE_TREND":
        return "TACTICAL_DEFENSIVE", "NEGATIVE_RECOMMENDATION_NEGATIVE_12M_ADJUSTED_RETURN_NEGATIVE_REGIME"
    if adjusted_return < 0.0:
        return "TACTICAL_CAUTION", "NEGATIVE_RECOMMENDATION_NEGATIVE_12M_ADJUSTED_RETURN_NONNEGATIVE_REGIME"
    return "TACTICAL_CONFLICT", "NEGATIVE_RECOMMENDATION_NONNEGATIVE_12M_ADJUSTED_RETURN"


def load_regime_context(csv_path: Path, manifest_path: Path) -> tuple[dict[str, dict], dict]:
    manifest = read_json(manifest_path)
    if manifest.get("status") != "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS":
        raise RuntimeError("Regime Probability V1 source is not PASS")
    if manifest.get("authority_id") != "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1":
        raise RuntimeError("unexpected Regime Probability V1 authority")
    if manifest.get("legacy_equivalent") is not False:
        raise RuntimeError("Regime Probability V1 must be non-legacy-equivalent")

    by_asset: dict[str, list[dict[str, str]]] = defaultdict(list)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            by_asset[str(row["universal_asset_id"])].append(row)

    context: dict[str, dict] = {}
    for asset_id, rows in sorted(by_asset.items()):
        total = sum(finite(row["probability"], "regime probability") for row in rows)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-10):
            raise RuntimeError(f"regime probabilities do not sum to one for {asset_id}: {total}")
        dominant_labels = {str(row["dominant_regime"]) for row in rows}
        dominant_probabilities = {round(finite(row["dominant_probability"], "dominant probability"), 12) for row in rows}
        as_of_dates = {str(row["as_of_date"]) for row in rows}
        if len(dominant_labels) != 1 or len(dominant_probabilities) != 1 or len(as_of_dates) != 1:
            raise RuntimeError(f"inconsistent regime context for {asset_id}")
        dominant = next(iter(dominant_labels))
        if dominant not in EXPECTED_REGIMES:
            raise RuntimeError(f"unsupported dominant regime for {asset_id}: {dominant}")
        context[asset_id] = {
            "dominant_regime": dominant,
            "dominant_regime_probability": next(iter(dominant_probabilities)),
            "as_of_date": next(iter(as_of_dates)),
        }
    return context, manifest


def load_uncertainty_context(csv_path: Path, manifest_path: Path, tactical_horizon: int) -> tuple[dict[str, dict], dict]:
    manifest = read_json(manifest_path)
    if manifest.get("status") != "METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1_PASS":
        raise RuntimeError("Uncertainty Adjusted V1 source is not PASS")
    if manifest.get("authority_id") != "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1":
        raise RuntimeError("unexpected Uncertainty Adjusted V1 authority")
    if manifest.get("legacy_equivalent") is not False:
        raise RuntimeError("Uncertainty Adjusted V1 must be non-legacy-equivalent")
    if manifest.get("scope") != "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON":
        raise RuntimeError("unexpected Uncertainty Adjusted V1 scope")

    context: dict[str, dict] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["horizon_months"]) != tactical_horizon:
                continue
            asset_id = str(row["universal_asset_id"])
            if asset_id in context:
                raise RuntimeError(f"duplicate {tactical_horizon}-month uncertainty row for {asset_id}")
            context[asset_id] = {
                "as_of_date": str(row["as_of_date"]),
                "adjusted_expected_return": finite(row["adjusted_expected_return"], "adjusted expected return"),
                "dominant_regime": str(row["dominant_regime"]),
                "dominant_regime_probability": finite(row["dominant_regime_probability"], "dominant regime probability"),
            }
    if len(context) != int(manifest.get("asset_count", -1)):
        raise RuntimeError("tactical-horizon uncertainty asset count does not match manifest")
    return context, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--regime-probability-csv", type=Path, required=True)
    parser.add_argument("--regime-probability-manifest", type=Path, required=True)
    parser.add_argument("--uncertainty-adjusted-csv", type=Path, required=True)
    parser.add_argument("--uncertainty-adjusted-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    methodology = read_json(args.methodology)
    native_cycle = read_json(args.native_cycle)

    if contract.get("authority_id") != "UIP_NATIVE_METALS_TACTICAL_STATE_V1":
        raise RuntimeError("unexpected Tactical State V1 authority")
    if contract.get("scope") != "BENCHMARK_COMMODITY_ASSET_ONLY":
        raise RuntimeError("unexpected Tactical State V1 scope")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("Tactical State V1 must remain non-legacy-equivalent")
    if contract.get("source_state_mode") != "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY":
        raise RuntimeError("unsupported source-state mode")
    if native_cycle.get("status") != "PASS":
        raise RuntimeError("current native cycle is not PASS")

    models = methodology.get("models") or []
    if not models or not isinstance(models[0], dict):
        raise RuntimeError("methodology registry is missing model definition")
    model_id = str(models[0].get("model_id", ""))
    source_methodology_version = str(methodology.get("registry_version", ""))
    if model_id != contract.get("model_id"):
        raise RuntimeError("contract model_id does not match methodology registry")

    tactical_horizon = int(contract.get("tactical_horizon_months", 0))
    if tactical_horizon != 12:
        raise RuntimeError("Tactical State V1 requires the governed 12-month tactical horizon")

    regime_context, regime_manifest = load_regime_context(args.regime_probability_csv, args.regime_probability_manifest)
    uncertainty_context, uncertainty_manifest = load_uncertainty_context(
        args.uncertainty_adjusted_csv, args.uncertainty_adjusted_manifest, tactical_horizon
    )

    minimum = contract.get("minimum_evidence") or {}
    required_true = (
        "native_recommendation_required",
        "uncertainty_adjusted_v1_12_month_row_required",
        "regime_probability_v1_context_required",
        "same_as_of_date_required",
    )
    if not all(minimum.get(key) is True for key in required_true):
        raise RuntimeError("Tactical State V1 minimum evidence contract is incomplete")
    if minimum.get("insufficient_evidence_behavior") != "FAIL_CLOSED":
        raise RuntimeError("Tactical State V1 must fail closed on insufficient evidence")

    recommendations: dict[str, set[str]] = defaultdict(set)
    as_of_by_asset: dict[str, set[str]] = defaultdict(set)
    for row in native_cycle.get("forecasts") or []:
        source_asset = str(row.get("asset_id", "")).strip()
        if not source_asset:
            raise RuntimeError("native forecast missing asset_id")
        universal_asset_id = f"metals:commodity:{source_asset.lower()}"
        recommendation = str(row.get("recommendation", "")).strip()
        if recommendation not in EXPECTED_RECOMMENDATIONS:
            raise RuntimeError(f"unsupported native recommendation for {universal_asset_id}: {recommendation}")
        if str(row.get("model_id", "")) != model_id:
            raise RuntimeError(f"model mismatch for {universal_asset_id}")
        if str(row.get("methodology_version", "")) != source_methodology_version:
            raise RuntimeError(f"methodology mismatch for {universal_asset_id}")
        recommendations[universal_asset_id].add(recommendation)
        as_of_by_asset[universal_asset_id].add(str(row.get("as_of_date", "")))

    if not recommendations:
        raise RuntimeError("native cycle contains no forecasts")
    if any(len(values) != 1 for values in recommendations.values()):
        raise RuntimeError("native recommendation is not consistent across forecast horizons")
    if any(len(values) != 1 or "" in values for values in as_of_by_asset.values()):
        raise RuntimeError("native as-of date is missing or inconsistent across forecast horizons")

    assets = set(recommendations)
    if set(regime_context) != assets or set(uncertainty_context) != assets:
        raise RuntimeError("native, regime, and uncertainty asset universes differ")

    rows_out: list[dict[str, object]] = []
    states: set[str] = set()
    for asset_id in sorted(assets):
        recommendation = next(iter(recommendations[asset_id]))
        native_as_of = next(iter(as_of_by_asset[asset_id]))
        regime = regime_context[asset_id]
        uncertainty = uncertainty_context[asset_id]
        if not (native_as_of == regime["as_of_date"] == uncertainty["as_of_date"]):
            raise RuntimeError(f"source as-of mismatch for {asset_id}")
        if uncertainty["dominant_regime"] != regime["dominant_regime"]:
            raise RuntimeError(f"regime label mismatch for {asset_id}")
        if not math.isclose(
            uncertainty["dominant_regime_probability"], regime["dominant_regime_probability"], rel_tol=0.0, abs_tol=1e-10
        ):
            raise RuntimeError(f"regime probability mismatch for {asset_id}")

        tactical_state, state_reason = classify_tactical_state(
            recommendation,
            uncertainty["adjusted_expected_return"],
            regime["dominant_regime"],
        )
        rows_out.append(
            {
                "universal_asset_id": asset_id,
                "as_of_date": native_as_of,
                "tactical_horizon_months": tactical_horizon,
                "recommendation": recommendation,
                "adjusted_expected_return": round(uncertainty["adjusted_expected_return"], 12),
                "dominant_regime": regime["dominant_regime"],
                "dominant_regime_probability": round(regime["dominant_regime_probability"], 12),
                "tactical_state": tactical_state,
                "state_reason": state_reason,
                "model_id": model_id,
                "source_methodology_version": source_methodology_version,
                "authority_id": contract["authority_id"],
                "methodology_version": contract["methodology_version"],
                "state_interpretation": contract["state_interpretation"],
            }
        )
        states.add(tactical_state)

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "metals_tactical_state.csv"
    fields = list(contract["required_output_fields"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_out)

    manifest = {
        "status": "METALS_NATIVE_TACTICAL_STATE_V1_PASS",
        "authority_id": contract["authority_id"],
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": contract["scope"],
        "source_state_mode": contract["source_state_mode"],
        "state_interpretation": contract["state_interpretation"],
        "output_grain": contract["output_grain"],
        "tactical_horizon_months": tactical_horizon,
        "recommendation_semantics": contract["recommendation_semantics"],
        "uncertainty_semantics": contract["uncertainty_semantics"],
        "regime_semantics": contract["regime_semantics"],
        "risk_semantics": contract["risk_semantics"],
        "taxonomy": contract["taxonomy"],
        "observed_states": sorted(states),
        "row_count": len(rows_out),
        "asset_count": len(assets),
        "model_id": model_id,
        "source_methodology_version": source_methodology_version,
        "regime_probability_authority_id": regime_manifest.get("authority_id"),
        "regime_probability_methodology_version": regime_manifest.get("methodology_version"),
        "uncertainty_adjusted_authority_id": uncertainty_manifest.get("authority_id"),
        "uncertainty_adjusted_methodology_version": uncertainty_manifest.get("methodology_version"),
        "contract_sha256": sha256_file(args.contract),
        "methodology_registry_sha256": sha256_file(args.methodology),
        "native_cycle_sha256": sha256_file(args.native_cycle),
        "regime_probability_csv_sha256": sha256_file(args.regime_probability_csv),
        "regime_probability_manifest_sha256": sha256_file(args.regime_probability_manifest),
        "uncertainty_adjusted_csv_sha256": sha256_file(args.uncertainty_adjusted_csv),
        "uncertainty_adjusted_manifest_sha256": sha256_file(args.uncertainty_adjusted_manifest),
        "output_sha256": sha256_file(csv_path),
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_rows_copied_forward": False,
        "legacy_action_mapping_reused": False,
        "legacy_classifier_reused": False,
        "vehicle_risk_projection_performed": False,
        "vehicle_tactical_projection_performed": False,
        "missing_state_imputed": False,
        "statistical_calibration_claimed": False,
        "cross_asset_ranking_performed": False,
        "portfolio_allocation_performed": False,
        "trade_sizing_performed": False,
        "automatic_execution_performed": False,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_TACTICAL_STATE_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

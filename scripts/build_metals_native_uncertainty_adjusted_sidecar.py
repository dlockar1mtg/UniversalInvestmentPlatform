"""Build UIP-native Metals Uncertainty Adjusted V1 from current certified native forecasts."""
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


def finite(value: object, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite {name}: {value}")
    return number


def compute_adjustment(raw_expected_return: float, confidence: float) -> tuple[float, float]:
    if not 0.0 <= confidence <= 1.0:
        raise RuntimeError(f"confidence out of range: {confidence}")
    uncertainty_penalty = abs(raw_expected_return) * (1.0 - confidence)
    adjusted_expected_return = raw_expected_return - uncertainty_penalty
    if uncertainty_penalty < -1e-15:
        raise RuntimeError("uncertainty penalty must be nonnegative")
    if adjusted_expected_return > raw_expected_return + 1e-15:
        raise RuntimeError("adjusted expected return cannot exceed raw expected return")
    return uncertainty_penalty, adjusted_expected_return


def load_regime_context(csv_path: Path, manifest_path: Path) -> tuple[dict[str, dict], dict]:
    manifest = read_json(manifest_path)
    if manifest.get("status") != "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS":
        raise RuntimeError("Regime Probability V1 source is not PASS")
    if manifest.get("authority_id") != "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1":
        raise RuntimeError("unexpected Regime Probability V1 authority")
    if manifest.get("legacy_equivalent") is not False:
        raise RuntimeError("Regime Probability V1 must be non-legacy-equivalent")
    if manifest.get("statistical_calibration_claimed") is not False:
        raise RuntimeError("Regime Probability V1 cannot be treated as statistically calibrated")

    by_asset: dict[str, list[dict[str, str]]] = defaultdict(list)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            by_asset[str(row["universal_asset_id"])].append(row)

    context: dict[str, dict] = {}
    for asset_id, rows in sorted(by_asset.items()):
        if len(rows) != int(manifest.get("regime_count", 0)):
            raise RuntimeError(f"unexpected regime row count for {asset_id}")
        total = sum(finite(row["probability"], "regime probability") for row in rows)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-10):
            raise RuntimeError(f"regime probabilities do not sum to one for {asset_id}: {total}")
        dominant_labels = {str(row["dominant_regime"]) for row in rows}
        dominant_probabilities = {
            round(finite(row["dominant_probability"], "dominant probability"), 12)
            for row in rows
        }
        as_of_dates = {str(row["as_of_date"]) for row in rows}
        if len(dominant_labels) != 1 or len(dominant_probabilities) != 1 or len(as_of_dates) != 1:
            raise RuntimeError(f"inconsistent regime context for {asset_id}")
        context[asset_id] = {
            "dominant_regime": next(iter(dominant_labels)),
            "dominant_regime_probability": next(iter(dominant_probabilities)),
            "as_of_date": next(iter(as_of_dates)),
        }

    if len(context) != int(manifest.get("asset_count", -1)):
        raise RuntimeError("Regime Probability V1 asset count does not match manifest")
    return context, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--regime-probability-csv", type=Path, required=True)
    parser.add_argument("--regime-probability-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    methodology = read_json(args.methodology)
    native_cycle = read_json(args.native_cycle)

    if contract.get("authority_id") != "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1":
        raise RuntimeError("unexpected uncertainty-adjusted authority")
    if contract.get("scope") != "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON":
        raise RuntimeError("unexpected uncertainty-adjusted scope")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("Uncertainty Adjusted V1 must remain non-legacy-equivalent")
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

    regime_context, regime_manifest = load_regime_context(
        args.regime_probability_csv,
        args.regime_probability_manifest,
    )

    minimum = contract.get("minimum_evidence") or {}
    if minimum.get("native_forecast_required") is not True:
        raise RuntimeError("native forecast must be required")
    if minimum.get("native_confidence_required") is not True:
        raise RuntimeError("native confidence must be required")
    if minimum.get("regime_probability_v1_asset_context_required") is not True:
        raise RuntimeError("Regime Probability V1 context must be required")
    if minimum.get("insufficient_evidence_behavior") != "FAIL_CLOSED":
        raise RuntimeError("Uncertainty Adjusted V1 must fail closed on insufficient evidence")

    forecasts = native_cycle.get("forecasts") or []
    if not forecasts:
        raise RuntimeError("native cycle contains no forecasts")

    rows_out: list[dict[str, object]] = []
    assets: set[str] = set()
    horizons: set[int] = set()
    as_of_dates: set[str] = set()

    seen_keys: set[tuple[str, int]] = set()
    for row in sorted(
        forecasts,
        key=lambda item: (str(item.get("asset_id", "")), int(item.get("horizon_months", 0))),
    ):
        source_asset = str(row.get("asset_id", "")).strip()
        if not source_asset:
            raise RuntimeError("native forecast missing asset_id")
        universal_asset_id = f"metals:commodity:{source_asset.lower()}"
        horizon = int(row.get("horizon_months", 0))
        if horizon <= 0:
            raise RuntimeError(f"invalid forecast horizon for {universal_asset_id}: {horizon}")
        key = (universal_asset_id, horizon)
        if key in seen_keys:
            raise RuntimeError(f"duplicate native forecast grain: {key}")
        seen_keys.add(key)

        if str(row.get("model_id", "")) != model_id:
            raise RuntimeError(f"model mismatch for {key}")
        if str(row.get("methodology_version", "")) != source_methodology_version:
            raise RuntimeError(f"methodology mismatch for {key}")

        raw_expected_return = finite(row.get("expected_return"), "expected_return")
        confidence = finite(row.get("confidence"), "confidence")
        penalty, adjusted = compute_adjustment(raw_expected_return, confidence)
        as_of_date = str(row.get("as_of_date", "")).strip()
        if not as_of_date:
            raise RuntimeError(f"missing as_of_date for {key}")

        regime = regime_context.get(universal_asset_id)
        if regime is None:
            raise RuntimeError(f"missing Regime Probability V1 context for {universal_asset_id}")
        if regime["as_of_date"] != as_of_date:
            raise RuntimeError(
                f"regime/native as-of mismatch for {universal_asset_id}: {regime['as_of_date']} != {as_of_date}"
            )

        rows_out.append(
            {
                "universal_asset_id": universal_asset_id,
                "as_of_date": as_of_date,
                "horizon_months": horizon,
                "raw_expected_return": round(raw_expected_return, 12),
                "confidence": round(confidence, 12),
                "uncertainty_penalty": round(penalty, 12),
                "adjusted_expected_return": round(adjusted, 12),
                "dominant_regime": regime["dominant_regime"],
                "dominant_regime_probability": round(regime["dominant_regime_probability"], 12),
                "model_id": model_id,
                "source_methodology_version": source_methodology_version,
                "authority_id": contract["authority_id"],
                "methodology_version": contract["methodology_version"],
                "adjustment_interpretation": contract["adjustment_interpretation"],
            }
        )
        assets.add(universal_asset_id)
        horizons.add(horizon)
        as_of_dates.add(as_of_date)

    if set(regime_context) != assets:
        raise RuntimeError("native forecast and Regime Probability V1 asset universes differ")

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "metals_uncertainty_adjusted.csv"
    fields = list(contract["required_output_fields"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_out)

    manifest = {
        "status": "METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1_PASS",
        "authority_id": contract["authority_id"],
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": contract["scope"],
        "source_state_mode": contract["source_state_mode"],
        "adjusted_quantity": contract["adjusted_quantity"],
        "adjustment_interpretation": contract["adjustment_interpretation"],
        "output_grain": contract["output_grain"],
        "formula": contract["formula"],
        "uncertainty_penalty_formula": contract["uncertainty_penalty_formula"],
        "confidence_semantics": contract["confidence_semantics"],
        "regime_semantics": contract["regime_semantics"],
        "risk_semantics": contract["risk_semantics"],
        "horizon_semantics": contract["horizon_semantics"],
        "row_count": len(rows_out),
        "asset_count": len(assets),
        "source_forecast_count": len(forecasts),
        "source_horizons_months": sorted(horizons),
        "source_as_of_dates": sorted(as_of_dates),
        "model_id": model_id,
        "source_methodology_version": source_methodology_version,
        "regime_probability_authority_id": regime_manifest.get("authority_id"),
        "regime_probability_methodology_version": regime_manifest.get("methodology_version"),
        "contract_sha256": sha256_file(args.contract),
        "methodology_registry_sha256": sha256_file(args.methodology),
        "native_cycle_sha256": sha256_file(args.native_cycle),
        "regime_probability_csv_sha256": sha256_file(args.regime_probability_csv),
        "regime_probability_manifest_sha256": sha256_file(args.regime_probability_manifest),
        "output_sha256": sha256_file(csv_path),
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "vehicle_risk_projection_performed": False,
        "regime_numeric_adjustment_performed": False,
        "commodity_to_vehicle_adjusted_projection_performed": False,
        "legacy_rows_copied_forward": False,
        "statistical_calibration_claimed": False,
        "cross_asset_ranking_performed": False,
        "portfolio_allocation_performed": False,
        "automatic_execution_performed": False,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build transparent UIP-native Metals model-component presentation sidecar."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

AUTHORITY_ID = "UIP_NATIVE_METALS_MODEL_COMPONENT_V1"
FORBIDDEN_LEGACY_NAMES = {"bayesian_shrinkage", "macro_view", "mean_reversion"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def transform(value: float, expression: str) -> float:
    if expression == "identity":
        return value
    if expression == "(value - 0.5) * 0.10":
        return (value - 0.5) * 0.10
    if expression == "zero":
        # Neutral anchor: the weight pulls the forecast toward 0 and contributes nothing.
        return 0.0
    raise RuntimeError(f"unsupported governed component transform: {expression}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/presentation/metals_model_component_v1.json"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    cycle = load_json(args.native_cycle)
    contract = load_json(args.contract)
    if contract.get("authority_id") != AUTHORITY_ID:
        raise RuntimeError("unexpected model-component authority_id")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("native model-component V1 must remain non-legacy-equivalent")
    if cycle.get("status") != "PASS":
        raise RuntimeError("passing UIP-native Metals cycle is required")

    forecasts = list(cycle.get("forecasts") or [])
    expected_forecasts = int(contract["expected_native_asset_count"]) * int(
        contract["expected_horizons_per_asset"]
    )
    if len(forecasts) != expected_forecasts:
        raise RuntimeError(
            f"unexpected forecast count: {len(forecasts)} != {expected_forecasts}"
        )

    component_contracts = list(contract["components"])
    weights = [float(item["model_weight"]) for item in component_contracts]
    if round(sum(weights), 10) != 1.0:
        raise RuntimeError("governed model-component weights must sum to 1.0")
    names = [str(item["model_name"]) for item in component_contracts]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate governed model names are not allowed")
    if FORBIDDEN_LEGACY_NAMES.intersection(names):
        raise RuntimeError("retired v8 model names must not be reused by native V1")

    required_component_keys = {
        str(item["source_component"]) for item in component_contracts
    }
    excluded = set(contract.get("excluded_evidence_fields") or [])
    rows: list[dict[str, object]] = []
    source_model_ids: set[str] = set()
    methodology_versions: set[str] = set()

    for forecast in forecasts:
        asset = str(forecast["asset_id"]).strip().upper()
        horizon = int(forecast["horizon_months"])
        as_of = str(forecast["as_of_date"])
        if len(as_of) != 10 or as_of[4] != "-" or as_of[7] != "-":
            raise RuntimeError(f"invalid forecast as_of_date: {as_of}")
        forecast_run_id = int(as_of.replace("-", ""))
        source_model_ids.add(str(forecast["model_id"]))
        methodology_versions.add(str(forecast["methodology_version"]))

        components = json.loads(str(forecast["component_json"]))
        missing = required_component_keys.difference(components)
        if missing:
            raise RuntimeError(f"missing native component(s) for {asset}/{horizon}: {sorted(missing)}")
        if not excluded.issubset(components):
            raise RuntimeError("expected evidence-only component fields are missing")

        for item in component_contracts:
            raw = float(components[str(item["source_component"])])
            signal = transform(raw, str(item["transform"]))
            rows.append(
                {
                    "forecast_run_id": forecast_run_id,
                    "metal": asset,
                    "horizon_months": horizon,
                    "model_name": str(item["model_name"]),
                    "model_forecast": f"{signal:.10f}",
                    "model_weight": f"{float(item['model_weight']):.10f}",
                }
            )

    expected_rows = expected_forecasts * int(contract["expected_components_per_forecast"])
    if len(rows) != expected_rows:
        raise RuntimeError(f"unexpected output row count: {len(rows)} != {expected_rows}")

    keys = [
        (row["forecast_run_id"], row["metal"], row["horizon_months"], row["model_name"])
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate model-component presentation keys are not allowed")

    fields = list(contract["required_output_fields"])
    if fields != list(rows[0].keys()):
        raise RuntimeError("builder fields do not match frozen V1 contract")

    rows.sort(
        key=lambda row: (
            int(row["forecast_run_id"]),
            str(row["metal"]),
            int(row["horizon_months"]),
            str(row["model_name"]),
        )
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / "metals_model_component.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "status": "METALS_NATIVE_MODEL_COMPONENT_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": contract["schema_version"],
        "legacy_equivalent": False,
        "row_count": len(rows),
        "forecast_count": len(forecasts),
        "asset_count": len({str(row["metal"]) for row in rows}),
        "horizon_count": len({int(row["horizon_months"]) for row in rows}),
        "component_count": len(component_contracts),
        "component_names": names,
        "source_model_ids": sorted(source_model_ids),
        "methodology_versions": sorted(methodology_versions),
        "output_sha256": sha256(output),
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "source_collection_performed": False,
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_MODEL_COMPONENT_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_native_model_component_v1_contract_and_builder(tmp_path: Path) -> None:
    contract_path = Path("config/presentation/metals_model_component_v1.json")
    contract = json.loads(contract_path.read_text())
    assert contract["authority_id"] == "UIP_NATIVE_METALS_MODEL_COMPONENT_V1"
    assert contract["legacy_equivalent"] is False
    assert sum(float(row["model_weight"]) for row in contract["components"]) == 1.0
    assert {row["model_name"] for row in contract["components"]}.isdisjoint(
        {"bayesian_shrinkage", "macro_view", "mean_reversion"}
    )

    forecasts = []
    for index in range(9):
        metal = f"METAL_{index}"
        for horizon in (12, 36, 60):
            components = {
                "benchmark_momentum": 0.10,
                "vehicle_confirmation": 0.20,
                "data_completeness": 1.0,
                "benchmark_observation_count": 12,
                "vehicle_series_count": 11,
            }
            forecasts.append(
                {
                    "asset_id": metal,
                    "horizon_months": horizon,
                    "as_of_date": "2026-09-10",
                    "current_value": 100.0,
                    "projected_value": 110.0,
                    "expected_return": 0.10,
                    "annualized_return": 0.125,
                    "confidence": 0.75,
                    "recommendation": "BUY",
                    "model_id": "uip_native_test_model",
                    "methodology_version": "test-v1",
                    "component_json": json.dumps(components, sort_keys=True),
                }
            )
    cycle_path = tmp_path / "cycle.json"
    cycle_path.write_text(json.dumps({"status": "PASS", "forecasts": forecasts}))
    output_root = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            "scripts/build_metals_native_model_component_sidecar.py",
            "--native-cycle",
            str(cycle_path),
            "--contract",
            str(contract_path),
            "--output-root",
            str(output_root),
        ],
        check=True,
    )

    manifest = json.loads((output_root / "manifest.json").read_text())
    assert manifest["status"] == "METALS_NATIVE_MODEL_COMPONENT_V1_PASS"
    assert manifest["row_count"] == 81
    assert manifest["forecast_count"] == 27
    assert manifest["asset_count"] == 9
    assert manifest["horizon_count"] == 3
    assert manifest["component_count"] == 3
    assert manifest["legacy_equivalent"] is False
    assert manifest["publication_staged"] is False
    assert manifest["publication_activated"] is False

    with (output_root / "metals_model_component.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 81
    first_by_name = {row["model_name"]: row for row in rows if row["metal"] == "METAL_0" and row["horizon_months"] == "12"}
    assert float(first_by_name["uip_native_benchmark_momentum"]["model_forecast"]) == 0.10
    assert float(first_by_name["uip_native_vehicle_confirmation"]["model_forecast"]) == 0.20
    assert float(first_by_name["uip_native_data_completeness_adjustment"]["model_forecast"]) == 0.05

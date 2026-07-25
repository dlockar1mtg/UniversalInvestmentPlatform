from __future__ import annotations

import csv
import json
from pathlib import Path

from exchange.metals.adapter.uip_native import publish_uip_native_metals_package
from foundation.production.metals_native_readiness import evaluate_native_readiness


def _cycle(path: Path) -> Path:
    document = {
        "status": "PASS",
        "forecasts": [
            {
                "asset_id": "GOLD",
                "horizon_months": 12,
                "as_of_date": "2026-07-25",
                "current_value": 2400.0,
                "projected_value": 2520.0,
                "expected_return": 0.05,
                "annualized_return": 0.05,
                "confidence": 0.7,
                "recommendation": "BUY",
                "model_id": "native-v1",
                "methodology_version": "1.0.0",
            }
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_publishes_required_universal_package_files(tmp_path: Path):
    result = publish_uip_native_metals_package(_cycle(tmp_path / "cycle.json"), tmp_path / "packages", run_id="run-1", generated_at_utc="2026-07-25T12:00:00Z")
    root = Path(result.package_root)
    assert (root / "export_manifest.csv").exists()
    assert (root / "platform_status.csv").exists()
    assert (root / "package_summary.json").exists()
    assert result.dataset_count == 4


def test_manifest_checksums_and_row_counts_pass_readiness(tmp_path: Path):
    result = publish_uip_native_metals_package(_cycle(tmp_path / "cycle.json"), tmp_path / "packages", run_id="run-1", generated_at_utc="2026-07-25T12:00:00Z")
    report = evaluate_native_readiness(Path(result.package_root))
    assert report.status == "PASS"
    assert report.reason_codes == ("UIP_NATIVE_METALS_READY",)
    assert report.external_dependency_count == 0


def test_readiness_fails_after_dataset_tampering(tmp_path: Path):
    result = publish_uip_native_metals_package(_cycle(tmp_path / "cycle.json"), tmp_path / "packages", run_id="run-1", generated_at_utc="2026-07-25T12:00:00Z")
    root = Path(result.package_root)
    with (root / "forecasts.csv").open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")
    report = evaluate_native_readiness(root)
    assert report.status == "FAILED"
    assert "CHECKSUM_MISMATCH" in report.reason_codes


def test_forecast_contract_columns_are_published(tmp_path: Path):
    result = publish_uip_native_metals_package(_cycle(tmp_path / "cycle.json"), tmp_path / "packages", run_id="run-1", generated_at_utc="2026-07-25T12:00:00Z")
    with (Path(result.package_root) / "forecasts.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["universal_asset_id"] == "metals:gold"
    assert row["forecast_horizon_months"] == "12"
    assert row["forecast_method"] == "native-v1"

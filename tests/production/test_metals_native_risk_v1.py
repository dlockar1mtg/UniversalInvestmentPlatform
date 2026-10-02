from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_native_risk_sidecar.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_risk_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-native-risk-v1-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("metals_native_risk_v1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_is_vehicle_only_and_nonlegacy():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_RISK_V1"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "VEHICLE_ONLY"
    assert contract["source_authority"] == "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
    assert contract["price_semantics"] == "UNADJUSTED_CLOSE"
    assert contract["expected_vehicle_count"] == 11
    assert contract["lookback_observations"] == 252
    assert contract["minimum_observations"] == 252
    assert contract["return_convention"] == "SIMPLE_CLOSE_TO_CLOSE_DAILY_RETURN"
    assert contract["annualization_factor"] == 252
    assert contract["methodology_version"] == "1.0.2"
    policy = contract["same_date_multi_source_policy"]
    assert policy["method"] == "LATEST_COLLECTED_REVISION_WINS"
    assert policy["latest_timestamp_tie_relative_tolerance"] == 1e-9
    assert policy["latest_timestamp_tie_absolute_tolerance"] == 1e-8
    assert policy["conflicting_latest_timestamp_tie_behavior"] == "FAIL_CLOSED"
    assert policy["missing_or_invalid_collected_at_behavior"] == "FAIL_CLOSED"
    assert contract["var"]["method"] == "HISTORICAL_EMPIRICAL"
    assert contract["var"]["confidence_level"] == 0.95
    assert "VEHICLE_TO_COMMODITY_RISK_PROJECTION" in contract["forbidden_semantics"]
    assert "LEGACY_RISK_ROW_COPY_FORWARD" in contract["forbidden_semantics"]
    assert "AVERAGE_CONFLICTING_SAME_DATE_SOURCE_CLOSES" in contract["forbidden_semantics"]
    assert "ARBITRARY_SOURCE_NAME_PRECEDENCE" in contract["forbidden_semantics"]


def test_math_helpers_are_deterministic():
    module = _load_module()
    assert module.linear_quantile([0.0, 1.0, 2.0, 3.0, 4.0], 0.25) == 1.0
    assert module.maximum_drawdown([100.0, 120.0, 90.0, 108.0]) == -0.25


def test_same_date_latest_collected_revision_wins():
    module = _load_module()
    rows = [
        {
            "ticker": "BIL",
            "observation_date": "2026-07-28",
            "close_usd": "91.62370300292969",
            "source_system": "source-a",
            "source_run_id": "run-old",
            "collected_at_utc": "2026-07-29T01:00:00Z",
        },
        {
            "ticker": "BIL",
            "observation_date": "2026-07-28",
            "close_usd": "91.62999725341797",
            "source_system": "source-b",
            "source_run_id": "run-new",
            "collected_at_utc": "2026-09-11T01:00:00Z",
        },
    ]
    canonical, collapsed, superseded = module.canonicalize_same_date_rows(
        "metals:vehicle:BIL",
        rows,
        tie_relative_tolerance=1e-9,
        tie_absolute_tolerance=1e-8,
    )
    assert len(canonical) == 1
    assert canonical[0]["close_usd"] == "91.62999725341797"
    assert collapsed == 1
    assert superseded == 1


def test_same_latest_timestamp_equivalent_rows_are_collapsed():
    module = _load_module()
    rows = [
        {
            "ticker": "BIL",
            "observation_date": "2026-09-10",
            "close_usd": "91.500000000",
            "source_system": "source-b",
            "source_run_id": "run-2",
            "collected_at_utc": "2026-09-11T00:00:00Z",
        },
        {
            "ticker": "BIL",
            "observation_date": "2026-09-10",
            "close_usd": "91.500000005",
            "source_system": "source-a",
            "source_run_id": "run-1",
            "collected_at_utc": "2026-09-11T00:00:00Z",
        },
    ]
    canonical, collapsed, superseded = module.canonicalize_same_date_rows(
        "metals:vehicle:BIL",
        rows,
        tie_relative_tolerance=1e-9,
        tie_absolute_tolerance=1e-8,
    )
    assert len(canonical) == 1
    assert canonical[0]["source_system"] == "source-a"
    assert collapsed == 1
    assert superseded == 0


def test_same_latest_timestamp_conflicting_rows_fail_closed():
    module = _load_module()
    rows = [
        {
            "ticker": "BIL",
            "observation_date": "2026-09-10",
            "close_usd": "91.50",
            "source_system": "source-a",
            "source_run_id": "run-1",
            "collected_at_utc": "2026-09-11T00:00:00Z",
        },
        {
            "ticker": "BIL",
            "observation_date": "2026-09-10",
            "close_usd": "91.75",
            "source_system": "source-b",
            "source_run_id": "run-2",
            "collected_at_utc": "2026-09-11T00:00:00Z",
        },
    ]
    with pytest.raises(RuntimeError, match="conflicting closes tied at latest collected_at_utc"):
        module.canonicalize_same_date_rows(
            "metals:vehicle:BIL",
            rows,
            tie_relative_tolerance=1e-9,
            tie_absolute_tolerance=1e-8,
        )


def test_missing_collected_at_fails_closed():
    module = _load_module()
    with pytest.raises(RuntimeError, match="missing collected_at_utc"):
        module.canonicalize_same_date_rows(
            "metals:vehicle:BIL",
            [{
                "ticker": "BIL",
                "observation_date": "2026-09-10",
                "close_usd": "91.50",
                "source_system": "source-a",
                "source_run_id": "run-1",
                "collected_at_utc": "",
            }],
            tie_relative_tolerance=1e-9,
            tie_absolute_tolerance=1e-8,
        )


def test_builder_produces_one_vehicle_row_per_series(tmp_path, monkeypatch):
    module = _load_module()
    # One series per enabled registered vehicle (the builder expects the registry universe).
    registry = json.loads(
        (Path(__file__).resolve().parents[2] / "config" / "metals" / "vehicles.json").read_text(encoding="utf-8-sig")
    )
    tickers = sorted(row["ticker"] for row in registry["vehicles"] if row.get("enabled", True))
    history_path = tmp_path / "metals_price_history.csv"
    fieldnames = [
        "asset_id", "ticker", "observation_date", "close_usd", "adjusted_close_usd",
        "volume", "price_semantics", "source_system", "source_authority",
        "source_package_id", "source_run_id", "collected_at_utc",
    ]
    rows = []
    start = date(2025, 1, 1)
    for series_index, ticker in enumerate(tickers):
        for index in range(252):
            drift = 1.0 + (index % 7 - 3) * 0.001
            price = (100.0 + series_index) * (1.0 + index * 0.0005) * drift
            rows.append({
                "asset_id": f"metals:vehicle:{ticker}",
                "ticker": ticker,
                "observation_date": str(start + timedelta(days=index)),
                "close_usd": f"{price:.8f}",
                "adjusted_close_usd": "",
                "volume": "1000",
                "price_semantics": "UNADJUSTED_CLOSE",
                "source_system": "test",
                "source_authority": "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
                "source_package_id": "test-package",
                "source_run_id": "test-run",
                "collected_at_utc": "2026-09-10T00:00:00Z",
            })
    duplicate = dict(rows[0])
    duplicate["source_system"] = "test-secondary"
    duplicate["source_run_id"] = "test-run-secondary"
    duplicate["close_usd"] = str(float(duplicate["close_usd"]) + 0.01)
    duplicate["collected_at_utc"] = "2026-09-11T00:00:00Z"
    rows.append(duplicate)

    with history_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    history_sha = hashlib.sha256(history_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "status": "METALS_NATIVE_HISTORY_SIDECARS_PASS",
        "source_authority": "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
        "history_row_count": len(rows),
        "files": {"metals_price_history.csv": {"row_count": len(rows), "sha256": history_sha}},
    }), encoding="utf-8")
    output_root = tmp_path / "risk"
    monkeypatch.setattr("sys.argv", [
        str(SCRIPT), "--history", str(history_path), "--history-manifest", str(manifest_path),
        "--contract", str(CONTRACT), "--output-root", str(output_root),
    ])
    assert module.main() == 0
    output_rows = list(csv.DictReader((output_root / "risk.csv").open(encoding="utf-8")))
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert len(output_rows) == len(tickers)
    assert {row["ticker"] for row in output_rows} == set(tickers)
    assert manifest["status"] == "METALS_NATIVE_RISK_V1_PASS"
    assert manifest["methodology_version"] == "1.0.2"
    assert manifest["legacy_equivalent"] is False
    assert manifest["row_count"] == len(tickers)
    assert manifest["raw_source_history_row_count"] == len(rows)
    assert manifest["canonical_unique_date_observation_count"] == len(tickers) * 252
    assert manifest["duplicate_source_rows_collapsed"] == 1
    assert manifest["superseded_conflicting_revision_rows"] == 1
    assert manifest["same_date_multi_source_method"] == "LATEST_COLLECTED_REVISION_WINS"
    assert manifest["conflicting_latest_timestamp_tie_behavior"] == "FAIL_CLOSED"
    assert manifest["source_collection_performed"] is False
    assert manifest["postgres_write_performed"] is False
    assert manifest["publication_staged"] is False
    assert manifest["publication_activated"] is False


def test_rehearsal_workflow_is_manual_and_artifact_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "build_metals_native_risk_sidecar.py" in text
    assert "native_rich_history/metals_price_history.csv" in text
    assert "native_risk_v1" in text
    assert "actions/upload-artifact@v4" in text
    assert "UIIP_DATABASE_URL" not in text

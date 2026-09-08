from __future__ import annotations

import csv
import hashlib
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
    assert row["universal_asset_id"] == "metals:commodity:gold"
    assert row["forecast_horizon_months"] == "12"
    assert row["forecast_method"] == "native-v1"


def test_canonical_native_asset_id_is_accepted(tmp_path: Path):
    cycle_path = tmp_path / "cycle.json"
    document = json.loads(_cycle(cycle_path).read_text(encoding="utf-8"))
    document["forecasts"][0]["asset_id"] = "METALS:COMMODITY:ALUMINUM"
    cycle_path.write_text(json.dumps(document), encoding="utf-8")

    result = publish_uip_native_metals_package(
        cycle_path,
        tmp_path / "packages",
        run_id="run-canonical-identity",
        generated_at_utc="2026-07-25T12:00:00Z",
    )

    with (
        Path(result.package_root) / "asset_master.csv"
    ).open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))

    assert row["universal_asset_id"] == "metals:commodity:aluminum"
    assert row["platform_asset_id"] == "METALS:COMMODITY:ALUMINUM"


def _governed_contract_columns(name: str) -> list[str]:
    root = Path(__file__).resolve().parents[2]
    path = root / "schemas" / "v1" / "csv" / f"{name}_columns.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [
            row["column_name"]
            for row in csv.DictReader(handle)
        ]


def test_benchmark_asset_master_does_not_invent_execution_authority(
    tmp_path: Path,
):
    result = publish_uip_native_metals_package(
        _cycle(tmp_path / "cycle.json"),
        tmp_path / "packages",
        run_id="run-asset-semantics",
        generated_at_utc="2026-07-25T12:00:00Z",
    )

    with (
        Path(result.package_root) / "asset_master.csv"
    ).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        row = next(reader)

    assert columns == _governed_contract_columns("asset_master")
    assert row["universal_asset_id"] == "metals:commodity:gold"
    assert row["asset_subclass"] == "commodity_benchmark"
    assert row["is_active"] == "True"
    assert row["investable"] == "False"

    # The canonical benchmark registry does not establish these authorities.
    assert row["market_or_region"] == ""
    assert row["liquidity_tier"] == ""
    assert row["first_available_date"] == ""


def test_recommendation_and_status_headers_match_governed_contracts(
    tmp_path: Path,
):
    result = publish_uip_native_metals_package(
        _cycle(tmp_path / "cycle.json"),
        tmp_path / "packages",
        run_id="run-contract",
        generated_at_utc="2026-07-25T12:00:00Z",
    )
    root = Path(result.package_root)

    with (root / "recommendations.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)
        recommendation_columns = list(reader.fieldnames or [])
        recommendation = next(reader)

    with (root / "platform_status.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)
        status_columns = list(reader.fieldnames or [])
        status = next(reader)

    assert recommendation_columns == _governed_contract_columns(
        "recommendations"
    )
    assert status_columns == _governed_contract_columns(
        "platform_status"
    )

    assert recommendation["recommendation"] == "buy"
    assert recommendation["normalized_score"] == "5.0"
    assert recommendation["confidence_score"] == "70.0"
    assert recommendation["platform_native_label"] == "BUY"
    assert recommendation["time_horizon"] == "12_month"
    assert recommendation["as_of_date"] == "2026-07-25"

    assert status["platform_id"] == "metals"
    assert status["platform_name"] == "Metals Intelligence Platform"
    assert status["platform_version"] == "1.0.0"
    assert status["run_status"] == "success"
    assert status["records_published"] == "1"
    assert status["warning_count"] == "0"
    assert status["error_count"] == "0"


def test_native_avoid_is_preserved_while_universal_action_is_not_ready(
    tmp_path: Path,
):
    cycle_path = tmp_path / "cycle.json"
    document = json.loads(_cycle(cycle_path).read_text(encoding="utf-8"))
    document["forecasts"][0]["recommendation"] = "AVOID"
    document["forecasts"][0]["expected_return"] = -0.20
    cycle_path.write_text(json.dumps(document), encoding="utf-8")

    result = publish_uip_native_metals_package(
        cycle_path,
        tmp_path / "packages",
        run_id="run-avoid",
        generated_at_utc="2026-07-25T12:00:00Z",
    )

    with (
        Path(result.package_root) / "recommendations.csv"
    ).open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))

    assert row["recommendation"] == "not_ready"
    assert row["platform_native_label"] == "AVOID"
    assert row["normalized_score"] == "0.0"
    assert row["confidence_score"] == "70.0"


def test_unknown_native_asset_fails_closed(tmp_path: Path):
    path = tmp_path / "cycle.json"
    document = json.loads(_cycle(path).read_text(encoding="utf-8"))
    document["forecasts"][0]["asset_id"] = "UNMAPPED_METAL"
    path.write_text(json.dumps(document), encoding="utf-8")

    try:
        publish_uip_native_metals_package(
            path,
            tmp_path / "packages",
            run_id="run-unknown",
            generated_at_utc="2026-07-25T12:00:00Z",
        )
    except ValueError as exc:
        assert "canonical registry" in str(exc)
    else:
        raise AssertionError("Unknown native Metals asset did not fail closed.")


def test_readiness_rejects_noncanonical_identity_even_with_valid_checksums(tmp_path: Path):
    result = publish_uip_native_metals_package(
        _cycle(tmp_path / "cycle.json"),
        tmp_path / "packages",
        run_id="run-identity",
        generated_at_utc="2026-07-25T12:00:00Z",
    )
    root = Path(result.package_root)

    affected = ("asset_master.csv", "forecasts.csv", "recommendations.csv")
    for filename in affected:
        path = root / filename
        text = path.read_text(encoding="utf-8")
        text = text.replace("metals:commodity:gold", "metals:gold")
        path.write_text(text, encoding="utf-8")

    manifest_path = root / "export_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    for row in rows:
        filename = row["filename"]
        if filename in affected:
            path = root / filename
            row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with path.open(newline="", encoding="utf-8") as handle:
                row["row_count"] = str(sum(1 for _ in csv.DictReader(handle)))
            row["file_size_bytes"] = str(path.stat().st_size)

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = evaluate_native_readiness(root)

    assert report.status == "FAILED"
    assert "NONCANONICAL_METALS_ASSET_ID" in report.reason_codes

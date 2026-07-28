from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from foundation.integrations.mtg.manual_production import (
    REQUIRED_ARTIFACTS,
    build_universal_package,
    validate_handoff,
)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_handoff(tmp_path: Path) -> tuple[Path, Path, dict]:
    mtg_root = tmp_path / "mtg"
    package = mtg_root / "data/operations/mtg_terminal_delivery/packages/test-mtg"
    package.mkdir(parents=True)

    interface_rows = []
    for index in range(1141):
        interface_rows.append({
            "canonical_product_id": f"MTG-{index:04d}",
            "canonical_product_name": f"Product {index}",
            "product_class": "SEALED",
            "selected_reference_price": "100" if index == 0 else "",
            "selected_reference_date": "2026-07-28" if index == 0 else "",
            "selected_source_type": "DIRECT_HISTORICAL_MARKET" if index == 0 else "NO_DEFENSIBLE_PRICE",
            "valuation_state": "DIRECT_HISTORY_VALUATION" if index == 0 else "VALUATION_UNAVAILABLE",
            "freshness_state": "FRESH_0_TO_7_DAYS" if index == 0 else "DATE_UNAVAILABLE",
            "dashboard_eligible": "true" if index == 0 else "false",
            "model_eligible": "true" if index == 0 else "false",
            "currency": "USD",
        })
    write_csv(package / "universal_mtg_consumption_interface.csv", list(interface_rows[0]), interface_rows)

    governed = [{
        **interface_rows[0],
        "forecast_method": "GOVERNED",
        "confidence": "HIGH",
        "forecast_consumption_state": "ELIGIBLE",
        "governed_forecast_eligible": "true",
        "one_year_downside_usd": "90",
        "one_year_base_usd": "110",
        "one_year_upside_usd": "120",
        "three_year_downside_usd": "100",
        "three_year_base_usd": "150",
        "three_year_upside_usd": "180",
        "five_year_downside_usd": "110",
        "five_year_base_usd": "200",
        "five_year_upside_usd": "250",
        "legacy_recommendation_action": "BUY",
        "recommendation_consumption_state": "ELIGIBLE",
        "governed_recommendation_eligible": "true",
        "guarded_rank": "1",
        "guarded_rank_score": "50",
        "suppression_reason": "",
    }]
    write_csv(package / "forecasts.csv", list(governed[0]), governed)
    write_csv(package / "recommendations.csv", list(governed[0]), governed)
    write_csv(package / "dashboard.csv", list(governed[0]), governed)
    write_csv(package / "rankings.csv", list(governed[0]), governed)
    write_csv(package / "exclusions.csv", list(governed[0]), governed)
    write_csv(
        package / "market_provenance.csv",
        ["canonical_product_id", "selected_source_type"],
        [{"canonical_product_id": row["canonical_product_id"], "selected_source_type": row["selected_source_type"]} for row in interface_rows],
    )
    (package / "consumption_summary.json").write_text("{}", encoding="utf-8")
    (package / "valuation_summary.json").write_text("{}", encoding="utf-8")
    artifacts = [{
        "filename": name,
        "sha256": sha256(package / name),
        "row_count": 1141 if name in {"universal_mtg_consumption_interface.csv", "market_provenance.csv"} else 1,
    } for name in REQUIRED_ARTIFACTS]
    handoff = {
        "status": "READY_FOR_UIP_IMPORT",
        "handoff_contract": "mtg-to-uip-manual-production-v1",
        "handoff_version": "1.0",
        "source_platform": "mtg",
        "package_id": "test-mtg",
        "package_relative_path": "data/operations/mtg_terminal_delivery/packages/test-mtg",
        "interface_name": "mtg-governed-terminal-delivery",
        "interface_version": "1.0",
        "governed_product_count": 1141,
        "current_asking_is_sold_history": False,
        "current_asking_model_eligible": False,
        "artifacts": artifacts,
    }
    handoff_path = mtg_root / "data/operations/mtg_uip_handoff/latest_mtg_uip_handoff.json"
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    return mtg_root, handoff_path, handoff


def test_valid_handoff_builds_universal_package(tmp_path: Path):
    mtg_root, handoff_path, expected = make_handoff(tmp_path)
    handoff, package = validate_handoff(mtg_root, handoff_path)
    assert handoff["package_id"] == expected["package_id"]

    output = build_universal_package(package, handoff, tmp_path / "uip/latest")
    with (output / "asset_master.csv").open(encoding="utf-8", newline="") as handle:
        assert sum(1 for _ in csv.DictReader(handle)) == 1141
    with (output / "forecasts.csv").open(encoding="utf-8", newline="") as handle:
        assert sum(1 for _ in csv.DictReader(handle)) == 3
    summary = json.loads((output / "package_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["source_handoff_contract"] == "mtg-to-uip-manual-production-v1"


def test_checksum_failure_stops_before_import(tmp_path: Path):
    mtg_root, handoff_path, _ = make_handoff(tmp_path)
    package = mtg_root / "data/operations/mtg_terminal_delivery/packages/test-mtg"
    (package / "forecasts.csv").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_handoff(mtg_root, handoff_path)
